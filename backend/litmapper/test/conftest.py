from contextlib import contextmanager

import pytest
from dramatiq import Worker
from sqlalchemy_utils.functions import create_database, database_exists, drop_database
from starlette.testclient import TestClient

from litmapper.db.util import DB_ENGINE, POSTGRES_URI, SessionLocal, get_db_dep
from litmapper.kv.util import get_kv, get_kv_dep
from litmapper.main import app
from litmapper.models import Base
from litmapper.tasks import LITMAPPER_QUEUE_NAME, broker


def pytest_addoption(parser):
    parser.addoption(
        "--keep-db",
        action="store_true",
        help="Don't drop the database after the test run finishes.",
    )
    parser.addoption(
        "--force-db",
        action="store_true",
        help="If the test DB already exists, drop it before running tests. "
        "This is dangerous if the test database might be accidentally pointing at a real "
        "database!",
    )


@pytest.fixture(scope="session")
def test_db(request):
    if database_exists(POSTGRES_URI):
        if request.config.getoption("force_db"):
            print(f"Dropping existing database at '{POSTGRES_URI}'.")
            drop_database(POSTGRES_URI)
        else:
            raise RuntimeError(f"Test database at '{POSTGRES_URI}' already exists.")

    create_database(POSTGRES_URI)
    Base.metadata.create_all(bind=DB_ENGINE, checkfirst=False)
    conn = DB_ENGINE.connect()
    try:
        yield conn
    finally:
        conn.close()

    if not request.config.getoption("keep_db"):
        drop_database(POSTGRES_URI)


@pytest.fixture(scope="function")
def db_txn(test_db):
    # Run tests inside of a transaction which can be rolled back afterward
    trans = test_db.begin()
    sess = SessionLocal(bind=test_db)

    yield sess

    sess.close()
    trans.rollback()


@pytest.fixture(scope="function")
def test_kv(request):
    # Yield a client connection to the kv store and clear it after each test run
    with get_kv() as kv:
        yield kv

    kv.flushall()


@pytest.fixture(scope="function")
def api_client(db_txn, test_kv):
    # Override the DB dependency to use the fixture running in a transaction,
    # so the API server sees the database within the same transaction as all the
    # tests.
    app.dependency_overrides[get_db_dep] = lambda: db_txn
    # Use the test key-value store connection as well
    app.dependency_overrides[get_kv_dep] = lambda: test_kv
    return TestClient(app)


@pytest.fixture(scope="function")
def dramatiq_broker():
    broker.flush_all()
    return broker


@pytest.fixture(scope="function")
def dramatiq_worker():
    worker = Worker(broker, worker_timeout=100)
    worker.start()
    yield worker
    worker.stop()


@pytest.fixture(scope="function")
def task_await(dramatiq_broker, dramatiq_worker):
    """
    Return a context manager which can be used to ensure
    all tasks run during it have finished and raised any
    errors encountered.
    """

    @contextmanager
    def _task_await():
        yield
        dramatiq_broker.join(LITMAPPER_QUEUE_NAME, fail_fast=True, timeout=None)
        dramatiq_worker.join()

    return _task_await
