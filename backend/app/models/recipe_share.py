from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecipeShare(Base):
    __tablename__ = "recipe_shares"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_recipe_id: Mapped[int] = mapped_column(
        ForeignKey("user_recipes.id"), nullable=False, unique=True
    )
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user_recipe: Mapped["UserRecipe"] = relationship(  # noqa: F821
        back_populates="share"
    )
