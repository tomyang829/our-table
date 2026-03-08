from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.recipes import router as recipes_router
from app.api.users import router as users_router
from app.core.config import settings

app = FastAPI(title="Our Table", version="0.1.0")

backend_root = Path(__file__).resolve().parent.parent
upload_path = backend_root / settings.UPLOAD_DIR
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

app.include_router(auth_router)
app.include_router(recipes_router)
app.include_router(users_router)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}
