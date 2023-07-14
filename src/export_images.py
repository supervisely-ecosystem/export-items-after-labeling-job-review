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

    progress = tqdm(total=len(images), desc=f"Downloading images...")
    for batch in sly.batched(images, batch_size=10):
        image_ids = [image_info.id for image_info in batch]
        image_names = [image_info.name for image_info in batch]

        ann_infos = api.annotation.download_batch(dataset.id, image_ids)
        ann_jsons = [ann_info.annotation for ann_info in ann_infos]

        if g.DOWNLOAD_ITEMS:
            batch_imgs_bytes = api.image.download_bytes(dataset.id, image_ids)
            for name, img_bytes, ann_json in zip(image_names, batch_imgs_bytes, ann_jsons):
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

        progress.update(len(batch))
