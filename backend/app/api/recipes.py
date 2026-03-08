import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
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
            },
        )

    return ExtractResponse(source_recipe=SourceRecipeResponse.model_validate(source))


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
    return UserRecipeResponse.model_validate(saved)


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
    return [UserRecipeResponse.model_validate(r) for r in recipes]


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
    return UserRecipeResponse.model_validate(recipe)


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

    await db.flush()
    await db.commit()
    return UserRecipeResponse.model_validate(recipe)
