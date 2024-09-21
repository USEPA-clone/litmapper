from redis import Redis

from litmapper import schemas
from litmapper.kv.info import JOBS_HASH_KEY, find_job, save_job


def test_find_job(test_kv: Redis):
    test_job = schemas.Job(
        job_id="test",
        status=schemas.JobStatus.SUCCESS,
        status_detail="test",
        result_url="http://test",
    )

    test_kv.hset(JOBS_HASH_KEY, key=test_job.job_id, value=test_job.json())

    assert find_job(test_kv, test_job.job_id) == test_job


def test_save_job(test_kv: Redis):
    test_job_create = schemas.JobCreate(
        status=schemas.JobStatus.SUCCESS,
        status_detail="test",
        result_url="http://test",
    )

    # Should save a JobCreate and assign an ID
    saved_job = save_job(test_kv, test_job_create)
    test_job = schemas.Job(**{**test_job_create.dict(), "job_id": saved_job.job_id})
    assert find_job(test_kv, saved_job.job_id) == test_job

    # Should modify the existing job
    test_job_new = schemas.Job(**{**test_job.dict(), "status_detail": "test2"})
    saved_new_job = save_job(test_kv, test_job_new)

    assert saved_new_job.job_id == saved_job.job_id
    assert find_job(test_kv, saved_new_job.job_id) == test_job_new
