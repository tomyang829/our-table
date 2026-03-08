from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: int
    email: str
    name: str | None = None
    avatar_url: str | None = None
    oauth_provider: str | None = None
    flavor_profile: dict | None = None

    model_config = ConfigDict(from_attributes=True)


class FlavorProfileUpdate(BaseModel):
    flavor_profile: dict
