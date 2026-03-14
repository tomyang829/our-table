from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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
    servings: str | None = None
    extracted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractResponse(BaseModel):
    source_recipe: SourceRecipeResponse
    # True when the page had no recipe schema markup; ingredients/instructions
    # will be empty and the user should fill them in manually.
    partial_parse: bool = False


class UserRecipeSaveRequest(BaseModel):
    notes: str | None = None


class UserRecipeCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    ingredients: list[str] = Field(default_factory=list)
    instructions: list[str] = Field(default_factory=list)
    notes: str | None = None
    servings: str | None = None


class UserRecipeUpdate(BaseModel):
    title: str | None = None
    ingredients: list | None = None
    instructions: list | None = None
    notes: str | None = None
    servings: str | None = None


class UserRecipeResponse(BaseModel):
    id: int
    user_id: int
    source_recipe_id: int
    title: str | None
    ingredients: list | None
    instructions: list | None
    notes: str | None
    image_url: str | None = None
    servings: str | None = None
    created_at: datetime
    updated_at: datetime
    source_recipe: SourceRecipeResponse | None = None
    deviates_from_source: bool = False

    model_config = ConfigDict(from_attributes=True)
