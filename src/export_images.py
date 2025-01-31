import os
from typing import List
import supervisely as sly

from tqdm import tqdm

import globals as g


def export_images(
    api: sly.Api,
    dataset: sly.Dataset,
    reviewed_item_ids: List[int],
    project_dir: str,
    project_meta: sly.ProjectMeta,
):
    # create local project and dataset
    project_fs = sly.Project(project_dir, sly.OpenMode.CREATE)
    project_fs.set_meta(project_meta)
    dataset_fs = project_fs.create_dataset(dataset.name)

    # get reviewed images infos
    all_images = api.image.get_list(dataset.id)
    images = [image for image in all_images if image.id in reviewed_item_ids]

    loop = sly.utils.get_or_create_event_loop()
        
    
    image_ids = [image_info.id for image_info in images]
    image_names = [image_info.name for image_info in images]

    progress_anns = tqdm(total=len(images), desc=f"Downloading annotations")
    ann_infos = loop.run_until_complete(api.annotation.download_bulk_async(dataset.id, image_ids, progress_cb=progress_anns))
    ann_jsons = [ann_info.annotation for ann_info in ann_infos]

    if g.DOWNLOAD_ITEMS:
        progress_images = tqdm(total=len(images), desc=f"Downloading images")
        imgs_bytes = loop.run_until_complete(api.image.download_bytes_many_async(dataset.id, image_ids, progress_cb=progress_images))
        for name, img_bytes, ann_json in zip(image_names, imgs_bytes, ann_jsons):
            if os.path.splitext(name)[1] == "":
                name = f"{name}.jpg"
            ann = sly.Annotation.from_json(ann_json, project_meta)
            dataset_fs.add_item_raw_bytes(name, img_bytes, ann)
    else:
        ann_dir = os.path.join(project_dir, dataset_fs.name, 'ann')
        sly.fs.mkdir(ann_dir)
        for name, ann_json in zip(image_names, ann_jsons):
            ann = sly.Annotation.from_json(ann_json, project_meta)
            sly.io.json.dump_json_file(ann_json, os.path.join(ann_dir, name + '.json'))

    progress.update(len(images))
