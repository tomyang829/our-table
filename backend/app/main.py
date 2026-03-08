from fastapi import FastAPI

from app.api.recipes import router as recipes_router

app = FastAPI(title="Our Table", version="0.1.0")

app.include_router(recipes_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
