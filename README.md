<!-- <div align="center" markdown> -->
<!-- <img src="https://user-images.githubusercontent.com/48245050/182545646-8af0b01f-d196-457f-a506-1cd2e0497f04.png"> -->

# Export items after passing the labeling job review

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#How-To-Run">How To Run</a> •
  <a href="#How-To-Use">How To Use</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/supervisely-ecosystem/export-items-after-labeling-job-review)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/export-items-after-labeling-job-review)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/export-items-after-labeling-job-review.png)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/export-items-after-labeling-job-review.png)](https://supervise.ly)

</div>

# Overview

Export **accepted items** (images, videos, point clouds) from dataset after labeling job review in Supervisely format. You can learn more about the Supervisely format and its structure by reading the [documentation](https://docs.supervise.ly/data-organization/00_ann_format_navi).

# How To Run

0. Create a labeling job, confirm items, submit it for review and review labels on items (accept or reject).

1. Run the app from the ecosystem or context menu of **Labeling Job** -> `Run app` -> `Export` -> `Export items after review`

> Only accepted items will be exported

<!-- <img src="https://user-images.githubusercontent.com/48913536/175984626-bea22e06-5275-4364-97f1-5083f8b0c234.png"/> -->

# How To Use

1. Wait for the app to process your data, once done, a link for download will become available

<!-- <img src="https://user-images.githubusercontent.com/48913536/175984683-417ffbb8-5c61-4206-9805-f766593d2bfe.png"/> -->

2. Result archive will be available for download by link at `Tasks` page or from `Team Files` by the following path:

- `tmp` -> `supervisely` -> `export` -> `Export items after review` -> `<task_id>` -> `reviewed items job_<job_id> project_<project_id>.tar.gz`
  <!-- <img src="https://user-images.githubusercontent.com/48913536/175984697-4066c217-8e93-4ba2-b916-1aabe77c2126.png"/> -->
