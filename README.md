<div align="center" markdown>
<img src="https://github.com/supervisely-ecosystem/export-items-after-labeling-job-review/assets/12828725/04184ec2-577f-4acc-af16-c33ddce44785">

# Export items after passing the labeling job review

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a> •
  <a href="#How-To-Use">How To Use</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](../../../../supervisely-ecosystem/export-items-after-labeling-job-review)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervisely.com/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/export-items-after-labeling-job-review)
[![views](https://app.supervisely.com/img/badges/views/supervisely-ecosystem/export-items-after-labeling-job-review.png)](https://supervisely.com)
[![runs](https://app.supervisely.com/img/badges/runs/supervisely-ecosystem/export-items-after-labeling-job-review.png)](https://supervisely.com)

</div>

# Overview

Export **accepted items** (images, videos, point clouds) from the dataset after labeling job review in Supervisely format. You can learn more about the Supervisely format, and its structure by reading the [documentation](https://docs.supervisely.com/data-organization/00_ann_format_navi).

Releases:

 - [**v1.0.4 release**](https://github.com/supervisely-ecosystem/export-items-after-labeling-job-review/releases/tag/v1.0.4): added an option for downloading only annotations without items.

# How To Run

0. Create a labeling job, confirm the items, submit it for review, and review the labels (accept or reject).

1. Run the app from the ecosystem or context menu of **Labeling Job** -> `Run app` -> `Export` -> `Export items after review`

> Only the accepted items will be exported

<img src="https://github.com/supervisely-ecosystem/export-items-after-labeling-job-review/assets/79905215/308cd774-fc0e-47a1-8ca8-22a7759aed7e"/>

# How To Use

1. Wait for the app to process your data, once done, a link for download will become available.

<img src="https://github.com/supervisely-ecosystem/export-items-after-labeling-job-review/assets/79905215/2eec8365-648f-41c9-b74d-0f6d9e9bde83"/>

2. Result archive will be available for download by link at `Tasks` page or from `Team Files` by the following path:

- `tmp` -> `supervisely` -> `export` -> `Export items after review` -> `<task_id>` -> `reviewed items job_<job_id> <project_name>_<project_id>.tar.gz`

<img src="https://github.com/supervisely-ecosystem/export-items-after-labeling-job-review/assets/79905215/9ddd2642-ee19-4a7b-a63e-24fe47f92469"/>
