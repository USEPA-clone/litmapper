import uuid
from typing import Union

from redis import Redis

from litmapper import errors, schemas

JOBS_HASH_KEY = "jobs"


def make_uuid() -> str:
    return uuid.uuid4().hex


def find_job(kv: Redis, job_id: str) -> schemas.Job:
    """
    Retrieve information on the given job from the database. Raises
    an appropriate error if the job doesn't exist.

    Args:
      kv: Key-value store connection
      job_id: ID for the job to retrieve

    Returns:
      Parsed job object
    """
    result_str = kv.hget(JOBS_HASH_KEY, job_id)

    if result_str is None:
        raise errors.ResourceDoesNotExist

    return schemas.Job.parse_raw(result_str)


def save_job(kv: Redis, job: Union[schemas.JobCreate, schemas.Job]) -> schemas.Job:
    """
    Save the given job information to the database, generating (if necessary)
    and returning a unique ID for the job.  Performs an "upsert", effectively.

    Args:
      kv: Key-value store connection
      job: Job information to save

    Returns:
      Created/updated Job object
    """
    if isinstance(job, schemas.JobCreate):
        job_id = make_uuid()
        save_job = schemas.Job(**job.dict(), job_id=job_id)
    else:
        job_id = job.job_id
        save_job = job

    kv.hset(JOBS_HASH_KEY, key=job_id, value=save_job.json())

    return save_job
