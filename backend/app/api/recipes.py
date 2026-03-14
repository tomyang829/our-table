import httpx
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.source_recipe import SourceRecipe
from app.models.user import User
from app.models.user_recipe import UserRecipe
from app.schemas.recipes import (
    ExtractRequest,
    ExtractResponse,
    SourceRecipeResponse,
    UserRecipeResponse,
    UserRecipeSaveRequest,
    UserRecipeUpdate,
)
from app.services.extractor import fetch_and_scrape

router = APIRouter(prefix="/api/recipes", tags=["recipes"])

ALLOWED_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _deviates_from_source(recipe: UserRecipe) -> bool:
    # User-uploaded image counts as an edit
    if recipe.image_url:
        return True
    if recipe.source_recipe is None:
        return False
    src = recipe.source_recipe
    if (recipe.title or "") != (src.title or ""):
        return True
    if (recipe.ingredients or []) != (src.ingredients or []):
        return True
    if (recipe.instructions or []) != (src.instructions or []):
        return True
    if (recipe.servings or "") != (src.servings or ""):
        return True
    return False


def _recipe_response(recipe: UserRecipe) -> UserRecipeResponse:
    resp = UserRecipeResponse.model_validate(recipe)
    resp.deviates_from_source = _deviates_from_source(recipe)
    return resp


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

    # Re-scrape when missing (new URL) or when we only have partial fallback data
    # from a previous run (e.g. title present but no ingredients/instructions).
    needs_rescrape = source is None or not source.title or (
        not source.ingredients and not source.instructions
    )
    if needs_rescrape:
        try:
            data = await fetch_and_scrape(url)
            # Never persist source-site images from scraped pages.
            data["image_url"] = None
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

        if source is None:
            source = SourceRecipe(url=url, **data)
            db.add(source)
        else:
            source.title = data.get("title")
            source.description = data.get("description")
            source.ingredients = data.get("ingredients")
            source.instructions = data.get("instructions")
            source.image_url = data.get("image_url")
            source.servings = data.get("servings")
        await db.flush()
        await db.commit()

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
                "source_recipe_id": source.id,
            },
        )

    partial = not source.ingredients and not source.instructions
    return ExtractResponse(
        source_recipe=SourceRecipeResponse.model_validate(source),
        partial_parse=partial,
    )


@router.post(
    "/source/{source_id}/save",
    response_model=UserRecipeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def save_recipe(
    source_id: int,
    body: UserRecipeSaveRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRecipeResponse:
    result = await db.execute(
        select(SourceRecipe).where(SourceRecipe.id == source_id)
    )
    source = result.scalar_one_or_none()
    if source is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source recipe not found",
        )

    user_recipe = UserRecipe(
        user_id=current_user.id,
        source_recipe_id=source.id,
        title=source.title,
        ingredients=source.ingredients,
        instructions=source.instructions,
        servings=source.servings,
        notes=body.notes if body else None,
    )
    db.add(user_recipe)
    await db.flush()
    await db.commit()

    result2 = await db.execute(
        select(UserRecipe)
        .where(UserRecipe.id == user_recipe.id)
        .options(selectinload(UserRecipe.source_recipe))
    )
    saved = result2.scalar_one()
    return _recipe_response(saved)


@router.get("/mine", response_model=list[UserRecipeResponse])
async def list_my_recipes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UserRecipeResponse]:
    result = await db.execute(
        select(UserRecipe)
        .where(UserRecipe.user_id == current_user.id)
        .options(selectinload(UserRecipe.source_recipe))
        .order_by(UserRecipe.created_at.desc())
    )
    recipes = result.scalars().all()
    return [_recipe_response(r) for r in recipes]


@router.get("/mine/{recipe_id}", response_model=UserRecipeResponse)
async def get_my_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRecipeResponse:
    result = await db.execute(
        select(UserRecipe)
        .where(UserRecipe.id == recipe_id, UserRecipe.user_id == current_user.id)
        .options(selectinload(UserRecipe.source_recipe))
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )
    return _recipe_response(recipe)


@router.post("/mine/{recipe_id}/image", response_model=UserRecipeResponse)
async def upload_recipe_image(
    recipe_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRecipeResponse:
    result = await db.execute(
        select(UserRecipe)
        .where(UserRecipe.id == recipe_id, UserRecipe.user_id == current_user.id)
        .options(selectinload(UserRecipe.source_recipe))
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid file type. Allowed: JPEG, PNG, WebP",
        )

    ext = ".jpg" if "jpeg" in content_type else ".png" if "png" in content_type else ".webp"
    max_size = 5 * 1024 * 1024  # 5 MB
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File too large. Maximum size is 5 MB.",
        )

    upload_dir = Path(settings.UPLOAD_DIR) / "recipes"
    upload_dir.mkdir(parents=True, exist_ok=True)
    path = upload_dir / f"{recipe_id}{ext}"
    path.write_bytes(contents)

    image_url = f"/api/uploads/recipes/{recipe_id}{ext}"
    recipe.image_url = image_url
    await db.flush()
    await db.commit()
    return _recipe_response(recipe)


@router.delete("/mine/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_recipe(
    recipe_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(UserRecipe).where(
            UserRecipe.id == recipe_id, UserRecipe.user_id == current_user.id
        )
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )
    await db.delete(recipe)
    await db.commit()


@router.put("/mine/{recipe_id}", response_model=UserRecipeResponse)
async def update_my_recipe(
    recipe_id: int,
    body: UserRecipeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRecipeResponse:
    result = await db.execute(
        select(UserRecipe)
        .where(UserRecipe.id == recipe_id, UserRecipe.user_id == current_user.id)
        .options(selectinload(UserRecipe.source_recipe))
    )
    recipe = result.scalar_one_or_none()
    if recipe is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    if body.title is not None:
        recipe.title = body.title
    if body.ingredients is not None:
        recipe.ingredients = body.ingredients
    if body.instructions is not None:
        recipe.instructions = body.instructions
    if body.notes is not None:
        recipe.notes = body.notes
    if body.servings is not None:
        recipe.servings = body.servings

    await db.flush()
    await db.commit()
    return _recipe_response(recipe)
