import os
from typing import List
import supervisely as sly
from supervisely.video_annotation.key_id_map import KeyIdMap

from tqdm import tqdm


def export_videos(
    api: sly.Api,
    dataset: sly.Dataset,
    reviewed_item_ids: List[int],
    project_dir: str,
    project_meta: sly.ProjectMeta,
):
    # create local project and dataset
    key_id_map = KeyIdMap()
    project_fs = sly.VideoProject(project_dir, sly.OpenMode.CREATE)
    project_fs.set_meta(project_meta)
    dataset_fs = project_fs.create_dataset(dataset.name)

    # get reviewed videos infos
    all_videos = api.video.get_list(dataset.id)
    videos = [video for video in all_videos if video.id in reviewed_item_ids]

    progress = tqdm(total=len(videos), desc=f"Downloading videos...")
    for batch in sly.batched(videos, batch_size=10):
        video_ids = [video_info.id for video_info in batch]
        video_names = [video_info.name for video_info in batch]
        ann_jsons = api.video.annotation.download_bulk(dataset.id, video_ids)
        for video_id, video_name, ann_json in zip(video_ids, video_names, ann_jsons):
            video_ann = sly.VideoAnnotation.from_json(ann_json, project_meta, key_id_map)
            if os.path.splitext(video_name)[1] == "":
                video_name = f"{video_name}.mp4"
            video_file_path = dataset_fs.generate_item_path(video_name)
            api.video.download_path(video_id, video_file_path)
            dataset_fs.add_item_file(
                video_name, video_file_path, ann=video_ann, _validate_item=False
            )

        progress.update(len(batch))

    project_fs.set_key_id_map(key_id_map)
