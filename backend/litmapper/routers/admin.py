import os

from alembic import command
from alembic.config import Config
from fastapi import APIRouter

router = APIRouter()


@router.post("/run_migrations", include_in_schema=False)
def run_migrations():
    try:
        alembic_cfg = Config("litmapper/alembic/alembic.ini")
        alembic_cfg.set_main_option("script_location", "litmapper/alembic")
        command.upgrade(alembic_cfg, "head")
        return {"success": True}
    except Exception as e:
        return {"failure": str(e), "path": os.getcwd()}
