import pytest

from app.config import ConfigError, load_settings

REQUIRED = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5433/db",
    "REDIS_URL": "redis://localhost:6379/0",
}


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Start from a clean slate: no inherited vars (tests also pass env_file=None).
    for name in [*REQUIRED, "CORS_ORIGINS", "APP_ENV"]:
        monkeypatch.delenv(name, raising=False)


def _set(monkeypatch: pytest.MonkeyPatch, **env: str) -> None:
    for name, value in env.items():
        monkeypatch.setenv(name, value)


@pytest.mark.unit
def test_loads_with_required_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, **REQUIRED)

    settings = load_settings(env_file=None)

    assert settings.database_url.scheme == "postgresql+asyncpg"
    assert settings.app_env == "dev"


@pytest.mark.unit
def test_missing_required_vars_fail_with_readable_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_settings(env_file=None)

    message = str(excinfo.value)
    assert "DATABASE_URL is required" in message
    assert "REDIS_URL is required" in message
    assert ".env.example" in message


@pytest.mark.unit
def test_rejects_sync_postgres_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, **{**REQUIRED, "DATABASE_URL": "postgresql://u:p@localhost/db"})

    with pytest.raises(ConfigError, match=r"DATABASE_URL .*postgresql\+asyncpg"):
        load_settings(env_file=None)


@pytest.mark.unit
def test_cors_origins_accepts_comma_separated_list(monkeypatch: pytest.MonkeyPatch) -> None:
    _set(monkeypatch, **REQUIRED, CORS_ORIGINS="http://a.test, http://b.test")

    assert load_settings(env_file=None).cors_origins == ["http://a.test", "http://b.test"]


@pytest.mark.unit
def test_reads_dotenv_file_but_real_env_wins(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"DATABASE_URL={REQUIRED['DATABASE_URL']}\nREDIS_URL=redis://from-file:6379/0\n"
    )
    monkeypatch.setenv("REDIS_URL", "redis://from-env:6379/0")

    settings = load_settings(env_file=env_file)

    assert str(settings.database_url) == REQUIRED["DATABASE_URL"]
    assert settings.redis_url.host == "from-env"
