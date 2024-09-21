from fastapi import APIRouter, Depends, HTTPException
from redis import Redis

from litmapper import errors, schemas
from litmapper.kv.info import find_job
from litmapper.kv.util import get_kv_dep

router = APIRouter()


@router.get(
    "/job/{job_id}",
    response_model=schemas.Job,
)
def get_job(
    job_id: str,
    kv: Redis = Depends(get_kv_dep),
):
    try:
        return find_job(kv, job_id)
    except errors.ResourceDoesNotExist:
        raise HTTPException(status_code=404, detail=f"No job found for ID: {job_id}")
