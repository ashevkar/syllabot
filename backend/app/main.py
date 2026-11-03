from fastapi import FastAPI

app = FastAPI(title="Syllabot API", version="0.0.0")


@app.get("/health")
async def health() -> dict[str, str]:
    # M1-02 extends this with DB and Redis checks.
    return {"status": "ok"}
