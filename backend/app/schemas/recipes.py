from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExtractRequest(BaseModel):
    url: str


class SourceRecipeResponse(BaseModel):
    id: int
    url: str
    title: str | None
    description: str | None
    ingredients: list | None
    instructions: list | None
    image_url: str | None
    extracted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractResponse(BaseModel):
    source_recipe: SourceRecipeResponse


class UserRecipeSaveRequest(BaseModel):
    notes: str | None = None


class UserRecipeUpdate(BaseModel):
    title: str | None = None
    ingredients: list | None = None
    instructions: list | None = None
    notes: str | None = None


class UserRecipeResponse(BaseModel):
    id: int
    user_id: int
    source_recipe_id: int
    title: str | None
    ingredients: list | None
    instructions: list | None
    notes: str | None
    image_url: str | None = None
    created_at: datetime
    updated_at: datetime
    source_recipe: SourceRecipeResponse | None = None
    deviates_from_source: bool = False

    model_config = ConfigDict(from_attributes=True)
