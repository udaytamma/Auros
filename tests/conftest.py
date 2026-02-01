import os
import importlib
import sys
import asyncio
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def test_app(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    os.environ["DISABLE_SCHEDULER"] = "true"
    os.environ["API_KEY"] = ""

    import api.config as config
    import api.db as db
    import api.models as models
    import api.main as main
    from api.db import init_db

    importlib.reload(config)
    importlib.reload(db)
    importlib.reload(models)
    importlib.reload(main)

    asyncio.run(init_db())
    asyncio.run(main._seed_companies())
    return main.app


@pytest.fixture()
def client(test_app):
    return TestClient(test_app)
