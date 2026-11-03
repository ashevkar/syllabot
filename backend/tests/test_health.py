from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import health


async def _ok(_: object) -> None:
    return None


async def _fail(_: object) -> None:
    raise ConnectionError("down")


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.mark.unit
def test_health_ok_when_all_dependencies_up(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(health, "check_database", _ok)
    monkeypatch.setattr(health, "check_redis", _ok)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "redis": "ok"}


@pytest.mark.unit
@pytest.mark.parametrize(
    ("db_check", "redis_check", "expected"),
    [
        (_fail, _ok, {"status": "degraded", "database": "error", "redis": "ok"}),
        (_ok, _fail, {"status": "degraded", "database": "ok", "redis": "error"}),
    ],
)
def test_health_503_when_a_dependency_is_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, db_check, redis_check, expected
) -> None:
    monkeypatch.setattr(health, "check_database", db_check)
    monkeypatch.setattr(health, "check_redis", redis_check)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == expected


@pytest.mark.unit
def test_health_reports_error_on_timeout(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _hang(_: object) -> None:
        import asyncio

        await asyncio.sleep(10)

    monkeypatch.setattr(health, "CHECK_TIMEOUT_S", 0.05)
    monkeypatch.setattr(health, "check_database", _hang)
    monkeypatch.setattr(health, "check_redis", _ok)

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "error"


@pytest.mark.unit
def test_openapi_schema_builds(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Syllabot API"
