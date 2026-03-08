from datetime import datetime, timezone

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SourceRecipe(Base):
    __tablename__ = "source_recipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    ingredients: Mapped[list | None] = mapped_column(JSONB)
    instructions: Mapped[list | None] = mapped_column(JSONB)
    image_url: Mapped[str | None] = mapped_column(Text)
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user_recipes: Mapped[list["UserRecipe"]] = relationship(  # noqa: F821
        back_populates="source_recipe", cascade="all, delete-orphan"
    )
