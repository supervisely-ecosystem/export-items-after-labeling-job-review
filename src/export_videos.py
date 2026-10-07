import os
import uuid
from typing import List
import supervisely as sly
import asyncio
from supervisely.video_annotation.key_id_map import KeyIdMap

from tqdm import tqdm

import globals as g


def drop_out_of_range_frames(ann_json: dict, video_id: int, video_name: str) -> dict:
    """Drop frames that lie outside the video, so one such video does not fail the whole export."""
    frames_count = ann_json.get("framesCount")
    in_range, skipped = [], []
    for frame in ann_json.get("frames", []):
        # same bounds VideoAnnotation.from_json enforces
        index = frame["index"]
        if index < 0 or (frames_count is not None and index > frames_count):
            skipped.append(frame)
        else:
            in_range.append(frame)
    if not skipped:
        return ann_json
    figures_count = sum(len(frame.get("figures", [])) for frame in skipped)
    sly.logger.warning(
        f"Video '{video_name}' (id: {video_id}) has {frames_count} frames, but {figures_count} "
        f"figure(s) are on frame(s) {[frame['index'] for frame in skipped]} outside it. "
        "They are skipped in the export; delete them in the video to remove this warning."
    )
    return {**ann_json, "frames": in_range}


def register_keys(ann_json: dict, key_id_map: KeyIdMap) -> dict:
    """Record keys and ids in key_id_map as VideoAnnotation.from_json does, without decoding masks.

    Parsing the whole annotation decodes every bitmap into a numpy array, which on mask-heavy
    videos takes many times the memory of the JSON itself. The JSON is written to the export as is.
    """

    def ensure_key(item: dict) -> uuid.UUID:
        # from_json generates a key when there is none, and to_json writes it out
        if "key" not in item:
            item["key"] = uuid.uuid4().hex
        return uuid.UUID(item["key"])

    key_id_map.add_video(ensure_key(ann_json), ann_json.get("videoId"))
    for tag in ann_json.get("tags", []):
        key_id_map.add_tag(ensure_key(tag), tag.get("id"))
    object_keys = {}
    for obj in ann_json.get("objects", []):
        key = ensure_key(obj)
        key_id_map.add_object(key, obj.get("id"))
        if obj.get("id") is not None:
            object_keys[obj["id"]] = key.hex
        for tag in obj.get("tags", []):
            ensure_key(tag)
    for frame in ann_json.get("frames", []):
        for figure in frame.get("figures", []):
            key_id_map.add_figure(ensure_key(figure), figure.get("id"))
            if "objectKey" not in figure and figure.get("objectId") in object_keys:
                figure["objectKey"] = object_keys[figure["objectId"]]
    return ann_json


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
            ann_json = drop_out_of_range_frames(ann_json, video_id, video_name)
            ann_json = register_keys(ann_json, key_id_map)
            if os.path.splitext(video_name)[1] == "":
                video_name = f"{video_name}.mp4"
            video_file_path = dataset_fs.generate_item_path(video_name)
            if g.DOWNLOAD_ITEMS:
                api.video.download_path(video_id, video_file_path)
            dataset_fs.add_item_file(
                video_name, video_file_path, ann=ann_json, _validate_item=False
            )

        progress.update(len(batch))

    project_fs.set_key_id_map(key_id_map)


def export_videos_async(
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

    loop = sly.fs.get_or_create_event_loop()
    progress_anns = tqdm(total=len(videos), desc=f"Downloading annotations")
    if g.DOWNLOAD_ITEMS:
        progress_vids = tqdm(total=len(videos), desc=f"Downloading videos")

    # process in batches so only one batch of annotations is held in memory at a time
    for batch in sly.batched(videos, batch_size=g.ASYNC_BATCH_SIZE):
        video_ids = [video_info.id for video_info in batch]
        video_names = [video_info.name for video_info in batch]
        ann_jsons = loop.run_until_complete(
            api.video.annotation.download_bulk_async(video_ids, progress_cb=progress_anns)
        )
        anns = [
            register_keys(drop_out_of_range_frames(ann_json, video_id, video_name), key_id_map)
            for video_id, video_name, ann_json in zip(video_ids, video_names, ann_jsons)
        ]
        video_file_paths = []
        for video_name in video_names:
            if os.path.splitext(video_name)[1] == "":
                video_name = f"{video_name}.mp4"
            video_file_paths.append(dataset_fs.generate_item_path(video_name))
        if g.DOWNLOAD_ITEMS:
            loop.run_until_complete(
                api.video.download_paths_async(
                    video_ids, video_file_paths, progress_cb=progress_vids
                )
            )

        coros = []
        for video_file_path, video_name, ann in zip(video_file_paths, video_names, anns):
            coros.append(
                dataset_fs.add_item_file_async(
                    video_name, video_file_path, ann=ann, _validate_item=False
                )
            )
        loop.run_until_complete(asyncio.gather(*coros))

    project_fs.set_key_id_map(key_id_map)
