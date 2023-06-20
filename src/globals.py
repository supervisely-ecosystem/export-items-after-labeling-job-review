import os
import supervisely as sly

from dotenv import load_dotenv

if sly.is_development():
    load_dotenv("local.env")
    load_dotenv(os.path.expanduser("~/supervisely.env"))

api = sly.Api.from_env()

JOB_ID = os.environ.get("modal.state.slyJobId")


if JOB_ID is None:
    raise RuntimeError("Job ID is not specified")

JOB = api.labeling_job.get_info_by_id(JOB_ID)
PROJECT = api.project.get_info_by_id(JOB.project_id)
DATASET = api.dataset.get_info_by_id(JOB.dataset_id)

if JOB is None or DATASET is None or PROJECT is None:
    raise RuntimeError("Job, project or dataset not found")
