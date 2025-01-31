import os
import supervisely as sly

from src.export_videos import export_videos
from src.export_images import export_images
from src.export_pointclouds import export_pointclouds
from supervisely.project.project import Project

import globals as g

items_type = " ".join(g.PROJECT.type.split("_"))
reviewed_item_ids = [item["id"] for item in g.JOB.entities if item["reviewStatus"] == "accepted"]

if g.DATASET.items_count < 1:
    sly.logger.warning(f"Dataset {g.DATASET.name} is empty")
elif len(reviewed_item_ids) < 1:
    sly.logger.warning(f"Not found {items_type} accepted by reviewer")
else:
    sly.logger.info(f"Found {len(reviewed_item_ids)} reviewed {items_type}")

    # make project directory path
    result_dirname = f"reviewed items job_{g.JOB.id} {g.PROJECT.name}_{g.PROJECT.id}"
    project_name = f"{g.PROJECT.name} (reviewed by job {g.JOB.id})"
    data_dir = sly.app.get_data_dir()
    result_dir = os.path.join(data_dir, result_dirname)
    project_dir = os.path.join(result_dir, project_name)
    result_archive = f"{result_dir}.tar.gz"

    # get project meta
    meta_json = g.api.project.get_meta(id=g.PROJECT.id)
    project_meta = sly.ProjectMeta.from_json(meta_json)

    sly.logger.info(f"Project type is {g.PROJECT.type}")
    loop = sly.fs.get_or_create_event_loop()
    if g.PROJECT.type == str(sly.ProjectType.VIDEOS):
        export_videos(g.api, g.DATASET, reviewed_item_ids, project_dir, project_meta)
    elif g.PROJECT.type == str(sly.ProjectType.IMAGES):
        try:
            coro = Project.download_async(
                g.api,
                g.PROJECT.id,
                project_dir,
                [g.DATASET.id],
                save_images=g.DOWNLOAD_ITEMS,
                images_ids=reviewed_item_ids,
            )
            loop.run_until_complete(coro)
        except Exception as e:
            sly.logger.error(
                f"Failed to download images with async. Switching to sync download", exc_info=True
            )
            export_images(g.api, g.DATASET, reviewed_item_ids, project_dir, project_meta)

    elif g.PROJECT.type == str(sly.ProjectType.POINT_CLOUDS):
        export_pointclouds(g.api, g.DATASET, reviewed_item_ids, project_dir, project_meta)
    else:
        raise RuntimeError(f"Project type {g.PROJECT.type} is not supported")

    sly.fs.archive_directory(result_dir, result_archive)
    sly.output.set_download(result_archive)

    reviewed = len(reviewed_item_ids)
    not_reviewed = g.DATASET.items_count - reviewed

    sly.logger.info(
        f"""
    Dataset {g.DATASET.name} has {g.DATASET.items_count} {items_type}:
        * {reviewed} reviewed {items_type} - processed;
        * {not_reviewed} not reviewed {items_type} - skipped.
    """
    )

g.app.shutdown()
