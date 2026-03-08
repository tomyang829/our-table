from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.recipes import router as recipes_router
from app.api.users import router as users_router

app = FastAPI(title="Our Table", version="0.1.0")

app.include_router(auth_router)
app.include_router(recipes_router)
app.include_router(users_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
