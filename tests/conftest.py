import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.dependencies.api import get_current_user
from app.dependencies.dao import get_vpc_repository


@pytest.fixture()
def client():
    # Minimal in-memory repo to satisfy /vpc routes
    store: dict[str, dict] = {}

    def _override_get_current_user():
        return "test-user"

    def _override_get_vpc_repository():
        class Repo:
            def save(self, record: dict) -> None:
                store[record["vpc_id"]] = record

            def get(self, vpc_id: str):
                return store.get(vpc_id)

            def list_all(self):
                return list(store.values())

            def delete(self, vpc_id: str) -> bool:
                return store.pop(vpc_id, None) is not None

        return Repo()

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_vpc_repository] = _override_get_vpc_repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
