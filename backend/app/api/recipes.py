import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.source_recipe import SourceRecipe
from app.models.user import User
from app.models.user_recipe import UserRecipe
from app.schemas.recipes import ExtractRequest, ExtractResponse, SourceRecipeResponse
from app.services.extractor import fetch_and_scrape

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.post("/extract", response_model=ExtractResponse)
async def extract_recipe(
    body: ExtractRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExtractResponse:
    url = str(body.url).rstrip("/")

    # Check if source_recipe already exists for this URL
    result = await db.execute(select(SourceRecipe).where(SourceRecipe.url == url))
    source = result.scalar_one_or_none()

    if source is None:
        # Scrape and create new source_recipe
        try:
            data = await fetch_and_scrape(url)
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to fetch URL: {exc.response.status_code}",
            )
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to reach URL: {exc}",
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not extract recipe from URL: {exc}",
            )

        source = SourceRecipe(url=url, **data)
        db.add(source)
        await db.flush()  # populate source.id without committing

    # Check if this user has already saved a recipe from this source
    dup_result = await db.execute(
        select(UserRecipe).where(
            UserRecipe.user_id == current_user.id,
            UserRecipe.source_recipe_id == source.id,
        )
    )
    existing = dup_result.scalar_one_or_none()

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "You have already saved this recipe",
                "existing_recipe_id": existing.id,
            },
        )

    return ExtractResponse(source_recipe=SourceRecipeResponse.model_validate(source))
