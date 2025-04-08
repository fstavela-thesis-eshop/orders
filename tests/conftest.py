from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.api.orders import get_db as orders_get_db  # type: ignore[attr-defined]
from src.main import app


@pytest.fixture(scope="session")
def api_client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def mock_db() -> MagicMock:
    return MagicMock(spec=Session)


@pytest.fixture(autouse=True)
def override_get_db(mock_db: MagicMock) -> Generator[None]:
    def _override() -> Generator[MagicMock]:
        yield mock_db

    app.dependency_overrides[orders_get_db] = _override

    yield

    app.dependency_overrides = {}
