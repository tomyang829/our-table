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
