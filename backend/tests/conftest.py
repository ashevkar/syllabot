import os

# Must run before `app.main` is imported: the app reads settings at import time.
# Nothing listens on these ports during unit tests; health checks are stubbed.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@127.0.0.1:1/test")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:1/0")
os.environ.setdefault("APP_ENV", "test")
