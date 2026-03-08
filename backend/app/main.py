from fastapi import FastAPI

app = FastAPI(title="Our Table", version="0.1.0")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
