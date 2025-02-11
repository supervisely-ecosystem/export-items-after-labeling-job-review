import os
from typing import List
import supervisely as sly
from supervisely.video_annotation.key_id_map import KeyIdMap
from supervisely.api.module_api import ApiField
from supervisely.io.json import dump_json_file
import asyncio

from tqdm import tqdm

import globals as g


def export_pointclouds(
    api: sly.Api,
    dataset: sly.Dataset,
    reviewed_item_ids: List[int],
    project_dir: str,
    project_meta: sly.ProjectMeta,
):
    # create local project and dataset
    key_id_map = KeyIdMap()
    project_fs = sly.PointcloudProject(project_dir, sly.OpenMode.CREATE)
    project_fs.set_meta(project_meta)
    dataset_fs = project_fs.create_dataset(dataset.name)

    # get reviewed pointcloud infos
    all_pointclouds = api.pointcloud.get_list(dataset.id)
    pointclouds = [pcd for pcd in all_pointclouds if pcd.id in reviewed_item_ids]

    progress = tqdm(total=len(pointclouds), desc=f"Downloading pointclouds...")
    for batch in sly.batched(pointclouds, batch_size=1):
        pointcloud_ids = [pointcloud_info.id for pointcloud_info in batch]
        pointcloud_names = [pointcloud_info.name for pointcloud_info in batch]

        ann_jsons = api.pointcloud.annotation.download_bulk(dataset.id, pointcloud_ids)

        for pointcloud_id, pointcloud_name, ann_json in zip(
            pointcloud_ids, pointcloud_names, ann_jsons
        ):
            pc_ann = sly.PointcloudAnnotation.from_json(ann_json, project_meta, key_id_map)
            pointcloud_file_path = dataset_fs.generate_item_path(pointcloud_name)

            if g.DOWNLOAD_ITEMS:
                api.pointcloud.download_path(pointcloud_id, pointcloud_file_path)
                related_images_path = dataset_fs.get_related_images_path(pointcloud_name)
                related_images = api.pointcloud.get_list_related_images(pointcloud_id)
                for rimage_info in related_images:
                    name = rimage_info[ApiField.NAME]
                    rimage_id = rimage_info[ApiField.ID]
                    path_img = os.path.join(related_images_path, name)
                    path_json = os.path.join(related_images_path, name + ".json")
                    api.pointcloud.download_related_image(rimage_id, path_img)
                    dump_json_file(rimage_info, path_json)

            dataset_fs.add_item_file(
                pointcloud_name, pointcloud_file_path, ann=pc_ann, _validate_item=False
            )

        progress.update(len(batch))

    project_fs.set_key_id_map(key_id_map)


def export_pointclouds_async(
    api: sly.Api,
    dataset: sly.Dataset,
    reviewed_item_ids: List[int],
    project_dir: str,
    project_meta: sly.ProjectMeta,
):
    # create local project and dataset
    key_id_map = KeyIdMap()
    project_fs = sly.PointcloudProject(project_dir, sly.OpenMode.CREATE)
    project_fs.set_meta(project_meta)
    dataset_fs = project_fs.create_dataset(dataset.name)

    # get reviewed pointcloud infos
    all_pointclouds = api.pointcloud.get_list(dataset.id)
    pointclouds = [pcd for pcd in all_pointclouds if pcd.id in reviewed_item_ids]
    loop = sly.fs.get_or_create_event_loop()
    progress_anns = tqdm(total=len(pointclouds), desc=f"Downloading annotations")

    pointcloud_ids = [pointcloud_info.id for pointcloud_info in pointclouds]
    pointcloud_names = [pointcloud_info.name for pointcloud_info in pointclouds]

    ann_jsons = loop.run_until_complete(
        api.pointcloud.annotation.download_bulk_async(pointcloud_ids, progress_cb=progress_anns)
    )
    pc_anns = [
        sly.PointcloudAnnotation.from_json(ann_json, project_meta, key_id_map)
        for ann_json in ann_jsons
    ]
    pointcloud_file_paths = [
        dataset_fs.generate_item_path(pointcloud_name) for pointcloud_name in pointcloud_names
    ]

    if g.DOWNLOAD_ITEMS:
        progress_pcds = tqdm(total=len(pointclouds), desc=f"Downloading pointclouds")
        loop.run_until_complete(
            api.pointcloud.download_paths_async(
                pointcloud_ids, pointcloud_file_paths, progress_cb=progress_pcds
            )
        )
        rimage_ids = []
        rimage_paths = []
        rimage_infos = []
        progress_collect_rimgs = tqdm(
            total=len(pointclouds), desc=f"Collecting related images info"
        )
        for pointcloud_name, pointcloud_id in zip(pointcloud_names, pointcloud_ids):
            related_images_path = dataset_fs.get_related_images_path(pointcloud_name)
            related_images = api.pointcloud.get_list_related_images(pointcloud_id)
            for rimage_info in related_images:
                rimage_infos.append(rimage_info)
                name = rimage_info[ApiField.NAME]
                rimage_ids.append(rimage_info[ApiField.ID])
                rimage_paths.append(os.path.join(related_images_path, name))
            progress_collect_rimgs.update(1)
        progress_rimgs = tqdm(total=len(rimage_ids), desc=f"Downloading related images")
        loop.run_until_complete(
            api.pointcloud.download_related_images_async(
                rimage_ids, rimage_paths, progress_cb=progress_rimgs
            )
        )
        for rimage_info, rimage_path in zip(rimage_infos, rimage_paths):
            dump_json_file(rimage_info, rimage_path + ".json")
    coros = []
    for pointcloud_name, pointcloud_file_path, pc_ann in zip(
        pointcloud_names, pointcloud_file_paths, pc_anns
    ):
        coros.append(
            dataset_fs.add_item_file_async(
                pointcloud_name, pointcloud_file_path, ann=pc_ann, _validate_item=False
            )
        )
    loop.run_until_complete(asyncio.gather(*coros))

    project_fs.set_key_id_map(key_id_map)
