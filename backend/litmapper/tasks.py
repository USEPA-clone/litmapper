import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Tuple

import dramatiq
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from dramatiq.brokers.stub import StubBroker
from dramatiq.encoder import JSONEncoder
from dramatiq.middleware import Shutdown
from pydantic import BaseModel
from pydantic.json import pydantic_encoder

from litmapper import schemas
from litmapper.db.util import get_db
from litmapper.kv.info import save_job
from litmapper.kv.util import get_kv, make_resource

LOGGER = logging.getLogger(__name__)


class PydanticJSONEncoder(JSONEncoder):
    """
    Custom dramatiq encoder allowing for Pydantic models to be JSON
    serialized and deserialized transparently.
    """

    @staticmethod
    def _serialize_pydantic(data: Dict[str, Any]):
        """
        Check the args and kwargs passed with the message for any Pydantic
        models.  Make a note of which args/kwargs need to be deserialized
        along with the name of the model they need to be deserialized into,
        so we know how to parse them when we decode.  Modifies the passed dict
        in-place.
        """
        pydantic_args: List[Tuple[int, str]] = []
        pydantic_kwargs: List[Tuple[str, str]] = []

        new_args: List[Any] = []
        for i, arg in enumerate(data["args"]):
            if isinstance(arg, BaseModel):
                pydantic_args.append((i, arg.__class__.__name__))
                arg = arg.dict()
            new_args.append(arg)
        data["args"] = tuple(new_args)

        for key, val in data["kwargs"].items():
            if isinstance(val, BaseModel):
                pydantic_kwargs.append((key, val.__class__.__name__))
                data["kwargs"][key] = val.dict()

        data["options"]["pydantic_args"] = pydantic_args
        data["options"]["pydantic_kwargs"] = pydantic_kwargs

    @staticmethod
    def _deserialize_pydantic(data: Dict[str, Any]):
        """
        Check the lists of args/kwargs that contain Pydantic models and deserialize
        them according to the class name stored with each.  Modifies the passed dict
        in-place.
        """

        new_args: List[Any] = list(data["args"])
        for i, class_name in data["options"]["pydantic_args"]:
            new_args[i] = getattr(schemas, class_name).parse_obj(new_args[i])
        data["args"] = tuple(new_args)

        for key, class_name in data["options"]["pydantic_kwargs"]:
            data["kwargs"][key] = getattr(schemas, class_name).parse_obj(
                data["kwargs"][key]
            )

    def encode(self, data: Dict[str, Any]) -> bytes:
        """
        Apply custom serialization to the task message itself and the pipe target
        component, if present
        """
        # Descend through an arbitrary number of pipeline targets in case this task
        # has dependencies -- need to serialize all of them with our custom method
        cur_dict = data
        while True:
            PydanticJSONEncoder._serialize_pydantic(cur_dict)
            if "pipe_target" in cur_dict["options"]:
                cur_dict = cur_dict["options"]["pipe_target"]
            else:
                break

        # Use the pydantic encoder to take advantage of helpful defaults for commonly
        # used types that aren't supported out of the box by json.dumps (ex enums)
        # These types _should_ all be automatically decodable by pydantic, but we'd have
        # to add some extra parsing logic similar to pydantic classes above if that
        # doesn't turn out to be true
        return json.dumps(data, separators=(",", ":"), default=pydantic_encoder).encode(
            "utf-8"
        )

    def decode(self, data: bytes) -> Dict[str, Any]:
        """
        Apply custom deserialization to the task message itself and the pipe target
        component, if present
        """
        data_dict = json.loads(data.decode("utf-8"))

        cur_dict = data_dict
        while True:
            PydanticJSONEncoder._deserialize_pydantic(cur_dict)
            if "pipe_target" in cur_dict["options"]:
                cur_dict = cur_dict["options"]["pipe_target"]
            else:
                break

        return data_dict


if os.getenv("DRAMATIQ_TEST_BROKER") is not None:
    broker = StubBroker()
    broker.emit_after("process_boot")
else:
    broker = RabbitmqBroker(host="rabbitmq")

dramatiq.set_broker(broker)
dramatiq.set_encoder(PydanticJSONEncoder())

LITMAPPER_QUEUE_NAME = "litmapper"


# Wrap the default dramatiq actor decorator to set more appropriate defaults


# for our application
def actor(fn=None, **kwargs) -> dramatiq.Actor:
    def decorator(fn):
        return dramatiq.actor(
            fn,
            queue_name=kwargs.pop("queue_name", LITMAPPER_QUEUE_NAME),
            max_retries=kwargs.pop("max_retries", 0),
            **kwargs,
        )

    if fn is None:
        return decorator
    return decorator(fn)


# For each type of resource, we provide a background task that can be run on a dramatiq
# worker to create it asynchronously.  Wrap that with a synchronous function that handles
# and returns the Job object used to keep track of the async job status.


@contextmanager
def worker_context(job: schemas.Job):
    """
    Create a common context and error handling for tasks running on a dramatiq worker
    """
    with get_kv() as kv:
        with get_db() as db:
            try:
                yield kv, db
            except (Exception, Shutdown) as e:
                LOGGER.error("Failing task due to exception/shutdown")
                job.status = schemas.JobStatus.FAILED
                job.status_detail = str(e)
                save_job(kv, job)
                raise


@actor
def make_filter_set(
    job: schemas.Job, params: schemas.FilterSetParams, force: bool = False
):
    with worker_context(job) as (kv, db):
        job.status_detail = "Creating filter set"
        save_job(kv, job)

        make_resource(kv, db, params, force=force)

        job.status = schemas.JobStatus.SUCCESS
        job.status_detail = None
        job.result_url = f"/literature/filter_set/{hash(params)}"
        save_job(kv, job)


@actor
def make_clustering(
    job: schemas.Job, params: schemas.ClusteringParams, force: bool = False
):
    with worker_context(job) as (kv, db):
        job.status_detail = "Creating filter set"
        save_job(kv, job)
        make_resource(kv, db, params.filter_set, force=force)

        job.status_detail = "Clustering"
        save_job(kv, job)
        make_resource(kv, db, params, force=force)

        job.status = schemas.JobStatus.SUCCESS
        job.status_detail = None
        job.result_url = f"/literature/clustering/{hash(params)}"
        save_job(kv, job)


@actor
def make_article_group(
    job: schemas.Job, params: schemas.ArticleGroupParams, force: bool = False
):
    with worker_context(job) as (kv, db):
        job.status_detail = "Creating filter set"
        save_job(kv, job)
        make_resource(kv, db, params.clustering.filter_set, force=force)

        job.status_detail = "Clustering"
        save_job(kv, job)
        make_resource(kv, db, params.clustering, force=force)

        job.status_detail = "Generating article group summaries"
        save_job(kv, job)
        make_resource(kv, db, params, force=force)

        job.status = schemas.JobStatus.SUCCESS
        job.status_detail = None
        job.result_url = f"/literature/article_group/{hash(params)}"
        save_job(kv, job)


def start_task(task: dramatiq.Actor, *args, **kwargs) -> schemas.Job:
    """
    Start a background task represented by a dramatiq actor.  Pass on a Job
    object which can be updated and saved to track job status and also pass through
    any other given arguments.

    Args:
      task: Actor to start
      *args: Positional args to pass to task
      **kwargs: Keyword args to pass to task

    Returns:
      The job object created for and used by the task
    """
    job_create = schemas.JobCreate(
        status=schemas.JobStatus.IN_PROGRESS,
        status_detail="Starting",
    )
    with get_kv() as kv:
        job = save_job(kv, job_create)
    task.send(job, *args, **kwargs)

    return job
