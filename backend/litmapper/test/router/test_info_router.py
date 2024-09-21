from redis import Redis
from starlette.testclient import TestClient

from litmapper import schemas
from litmapper.kv.info import save_job
from litmapper.test.util import require_response_code


def test_get_job(test_kv: Redis, api_client: TestClient):
    job = schemas.Job(
        job_id="test",
        status_detail="test",
        status=schemas.JobStatus.SUCCESS,
        result_url="http://test",
    )

    job_url = f"/info/job/{job.job_id}"
    res = api_client.get(job_url)
    require_response_code(res, 404)

    save_job(test_kv, job)

    res = api_client.get(job_url)
    require_response_code(res, 200)
    assert res.json() == job
