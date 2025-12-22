import re
from typing import Dict, List, Optional

import numpy as np
import supervisely as sly
from supervisely.api.module_api import ApiField
from supervisely.geometry.closed_surface_mesh import ClosedSurfaceMesh
from supervisely.geometry.mask_3d import Mask3D
from supervisely.io.fs import change_directory_at_index, touch
from supervisely.video_annotation.key_id_map import KeyIdMap
from supervisely.volume import stl_converter
from tqdm import tqdm

import globals as g


def _create_volume_header(ann: sly.VolumeAnnotation) -> Dict:
    header: Dict = {}
    header["sizes"] = np.array([value for _, value in ann.volume_meta["dimensionsIJK"].items()])
    world_matrix = ann.volume_meta["IJK2WorldMatrix"]
    header["space directions"] = np.array(
        [world_matrix[i : i + 3] for i in range(0, len(world_matrix) - 4, 4)]
    )
    header["space origin"] = np.array(
        [world_matrix[i + 3] for i in range(0, len(world_matrix) - 4, 4)]
    )
    if ann.volume_meta.get("ACS") == "RAS":
        header["space"] = "right-anterior-superior"
    elif ann.volume_meta.get("ACS") == "LAS":
        header["space"] = "left-anterior-superior"
    elif ann.volume_meta.get("ACS") == "LPS":
        header["space"] = "left-posterior-superior"
    return header


def _inject_figures_custom_data(
    api: sly.Api,
    dataset_id: int,
    volume_id: int,
    ann: sly.VolumeAnnotation,
) -> None:
    figs_map = api.volume.figure.download(dataset_id, [volume_id], skip_geometry=True) or {}
    figs = figs_map.get(volume_id, [])
    figs_ids_map = {fig.id: fig for fig in figs}
    for ann_fig in ann.figures + ann.spatial_figures:
        fig_info = figs_ids_map.get(getattr(ann_fig.geometry, "sly_id", None))
        if fig_info is not None and getattr(fig_info, "custom_data", None) is not None:
            ann_fig.custom_data.update(fig_info.custom_data)


def export_volumes(
    api: sly.Api,
    dataset: sly.Dataset,
    reviewed_item_ids: List[int],
    project_dir: str,
    project_meta: sly.ProjectMeta,
):
    # create local project and dataset
    key_id_map = KeyIdMap()
    project_fs = sly.VolumeProject(project_dir, sly.OpenMode.CREATE)
    project_fs.set_meta(project_meta)
    dataset_fs = project_fs.create_dataset(dataset.name)

    # get reviewed volume infos
    all_volumes = api.volume.get_list(dataset.id)
    volumes = [vol for vol in all_volumes if vol.id in reviewed_item_ids]

    progress = tqdm(total=len(volumes), desc="Downloading volumes...")
    for batch in sly.batched(volumes, batch_size=1):
        volume_ids = [volume_info.id for volume_info in batch]
        volume_names = [volume_info.name for volume_info in batch]

        ann_jsons = api.volume.annotation.download_bulk(dataset.id, volume_ids)

        for volume_info, volume_name, ann_json in zip(batch, volume_names, ann_jsons):
            if volume_name != ann_json[ApiField.VOLUME_NAME]:
                raise RuntimeError("Error in api.volume.annotation.download_bulk: broken order")

            ann = sly.VolumeAnnotation.from_json(ann_json, project_fs.meta, key_id_map)

            volume_file_path = dataset_fs.generate_item_path(volume_name)
            header: Optional[Dict] = None
            if g.DOWNLOAD_ITEMS:
                item_progress = tqdm(
                    desc=f"Downloading '{volume_name}'",
                    total=volume_info.sizeb,
                    unit="B",
                    unit_scale=True,
                    leave=False,
                )
                api.volume.download_path(
                    volume_info.id, volume_file_path, progress_cb=item_progress.update
                )
                item_progress.close()
            else:
                touch(volume_file_path)
                header = _create_volume_header(ann)

            mask_ids: List[int] = []
            mask_paths: List[str] = []
            mesh_ids: List[int] = []
            mesh_paths: List[str] = []
            for sf in ann.spatial_figures:
                figure_id = key_id_map.get_figure_id(sf.key())
                if sf.geometry.name() == Mask3D.name():
                    mask_ids.append(figure_id)
                    mask_paths.append(dataset_fs.get_mask_path(volume_name, sf))
                if sf.geometry.name() == ClosedSurfaceMesh.name():
                    mesh_ids.append(figure_id)
                    mesh_paths.append(dataset_fs.get_interpolation_path(volume_name, sf))

            _inject_figures_custom_data(api, dataset.id, volume_info.id, ann)

            api.volume.figure.download_stl_meshes(mesh_ids, mesh_paths)
            api.volume.figure.download_sf_geometries(mask_ids, mask_paths)

            # prepare a list of paths where converted STLs will be stored
            nrrd_paths: List[str] = []
            for file_path in mesh_paths:
                file_path = re.sub(r"\.[^.]+$", ".nrrd", file_path)
                file_path = change_directory_at_index(
                    file_path, "mask", -3
                )  # change destination folder
                nrrd_paths.append(file_path)

            stl_converter.to_nrrd(mesh_paths, nrrd_paths, header=header)

            ann, meta = api.volume.annotation._update_on_transfer(
                "download", ann, project_fs.meta, nrrd_paths
            )
            project_fs.set_meta(meta)

            dataset_fs.add_item_file(
                volume_name,
                volume_file_path,
                ann=ann,
                _validate_item=False,
            )

        progress.update(len(batch))

    project_fs.set_key_id_map(key_id_map)


def export_volumes_async(
    api: sly.Api,
    dataset: sly.Dataset,
    reviewed_item_ids: List[int],
    project_dir: str,
    project_meta: sly.ProjectMeta,
):
    # create local project and dataset
    key_id_map = KeyIdMap()
    project_fs = sly.VolumeProject(project_dir, sly.OpenMode.CREATE)
    project_fs.set_meta(project_meta)
    dataset_fs = project_fs.create_dataset(dataset.name)

    # get reviewed volume infos
    all_volumes = api.volume.get_list(dataset.id)
    volumes = [vol for vol in all_volumes if vol.id in reviewed_item_ids]
    volume_ids = [volume_info.id for volume_info in volumes]
    volume_names = [volume_info.name for volume_info in volumes]

    loop = sly.fs.get_or_create_event_loop()

    progress_anns = tqdm(total=len(volumes), desc="Downloading annotations")
    ann_jsons = loop.run_until_complete(
        api.volume.annotation.download_bulk_async(volume_ids, progress_cb=progress_anns.update)
    )
    progress_anns.close()

    # keep stable mapping by volume id
    ann_by_id = {ann_json.get(ApiField.VOLUME_ID): ann_json for ann_json in ann_jsons}

    volume_file_paths = [dataset_fs.generate_item_path(volume_name) for volume_name in volume_names]

    if g.DOWNLOAD_ITEMS:
        progress_vols = tqdm(total=len(volumes), desc="Downloading volumes")
        loop.run_until_complete(
            api.volume.download_paths_async(
                volume_ids,
                volume_file_paths,
                progress_cb=progress_vols.update,
                progress_cb_type="number",
            )
        )
        progress_vols.close()
        headers: List[Optional[Dict]] = [None] * len(volumes)
    else:
        headers = []
        for volume_file_path, ann_json in zip(
            volume_file_paths, [ann_by_id.get(i) for i in volume_ids]
        ):
            touch(volume_file_path)
            if ann_json is None:
                headers.append(None)
                continue
            tmp_ann = sly.VolumeAnnotation.from_json(ann_json, project_fs.meta, key_id_map)
            headers.append(_create_volume_header(tmp_ann))

    progress = tqdm(total=len(volumes), desc="Saving items")
    for volume_info, volume_name, volume_file_path, header in zip(
        volumes, volume_names, volume_file_paths, headers
    ):
        ann_json = ann_by_id.get(volume_info.id)
        if ann_json is None:
            raise RuntimeError(f"Missing volume annotation for volume id={volume_info.id}")
        if volume_name != ann_json[ApiField.VOLUME_NAME]:
            raise RuntimeError(
                "Error in api.volume.annotation.download_bulk_async: broken order/mapping"
            )

        ann = sly.VolumeAnnotation.from_json(ann_json, project_fs.meta, key_id_map)

        mask_ids: List[int] = []
        mask_paths: List[str] = []
        mesh_ids: List[int] = []
        mesh_paths: List[str] = []
        for sf in ann.spatial_figures:
            figure_id = key_id_map.get_figure_id(sf.key())
            if sf.geometry.name() == Mask3D.name():
                mask_ids.append(figure_id)
                mask_paths.append(dataset_fs.get_mask_path(volume_name, sf))
            if sf.geometry.name() == ClosedSurfaceMesh.name():
                mesh_ids.append(figure_id)
                mesh_paths.append(dataset_fs.get_interpolation_path(volume_name, sf))

        _inject_figures_custom_data(api, dataset.id, volume_info.id, ann)

        api.volume.figure.download_stl_meshes(mesh_ids, mesh_paths)
        api.volume.figure.download_sf_geometries(mask_ids, mask_paths)

        nrrd_paths: List[str] = []
        for file_path in mesh_paths:
            file_path = re.sub(r"\.[^.]+$", ".nrrd", file_path)
            file_path = change_directory_at_index(file_path, "mask", -3)
            nrrd_paths.append(file_path)

        stl_converter.to_nrrd(mesh_paths, nrrd_paths, header=header)

        ann, meta = api.volume.annotation._update_on_transfer(
            "download", ann, project_fs.meta, nrrd_paths
        )
        project_fs.set_meta(meta)

        dataset_fs.add_item_file(
            volume_name,
            volume_file_path,
            ann=ann,
            _validate_item=False,
        )

        progress.update(1)

    progress.close()
    project_fs.set_key_id_map(key_id_map)
