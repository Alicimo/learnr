from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from learnr.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


card_decks = Table(
    "card_decks",
    Base.metadata,
    Column("card_id", ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True),
    Column("deck_id", ForeignKey("decks.id", ondelete="CASCADE"), primary_key=True),
)

card_tags = Table(
    "card_tags",
    Base.metadata,
    Column("card_id", ForeignKey("cards.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    cards: Mapped[list["Card"]] = relationship(
        secondary=card_decks,
        back_populates="decks",
    )


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    cards: Mapped[list["Card"]] = relationship(
        secondary=card_tags,
        back_populates="tags",
    )


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        UniqueConstraint(
            "normalized_source",
            "normalized_target",
            "source_language",
            "target_language",
            name="uq_note_content_languages",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_text: Mapped[str] = mapped_column(Text)
    target_text: Mapped[str] = mapped_column(Text)
    normalized_source: Mapped[str] = mapped_column(String(512), index=True)
    normalized_target: Mapped[str] = mapped_column(String(512), index=True)
    source_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    cards: Mapped[list["Card"]] = relationship(back_populates="note", cascade="all, delete-orphan")


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (
        UniqueConstraint(
            "normalized_prompt",
            "normalized_answer",
            "direction",
            name="uq_card_prompt_answer_direction",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    direction: Mapped[str] = mapped_column(String(16), index=True)
    prompt_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    normalized_prompt: Mapped[str] = mapped_column(String(512), index=True)
    normalized_answer: Mapped[str] = mapped_column(String(512), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    note: Mapped[Note] = relationship(back_populates="cards")
    state: Mapped["CardState"] = relationship(
        back_populates="card",
        cascade="all, delete-orphan",
        uselist=False,
    )
    decks: Mapped[list[Deck]] = relationship(
        secondary=card_decks,
        back_populates="cards",
    )
    tags: Mapped[list[Tag]] = relationship(
        secondary=card_tags,
        back_populates="cards",
    )
    reviews: Mapped[list["Review"]] = relationship(back_populates="card")


class CardState(Base):
    __tablename__ = "card_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5)
    stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Float, nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    lapse_count: Mapped[int] = mapped_column(Integer, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    card: Mapped[Card] = relationship(back_populates="state")


class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    deck_id: Mapped[int | None] = mapped_column(ForeignKey("decks.id"), nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    target_count: Mapped[int] = mapped_column(Integer)
    completed_count: Mapped[int] = mapped_column(Integer, default=0)

    reviews: Mapped[list["Review"]] = relationship(back_populates="session")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    deck_id: Mapped[int | None] = mapped_column(ForeignKey("decks.id"), nullable=True, index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("review_sessions.id"), nullable=True, index=True)
    shown_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    time_to_reveal_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_to_grade_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    direction: Mapped[str] = mapped_column(String(16))
    correct: Mapped[bool] = mapped_column(Boolean)
    due_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_after: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval_before_days: Mapped[float] = mapped_column(Float)
    interval_after_days: Mapped[float] = mapped_column(Float)
    ease_before: Mapped[float] = mapped_column(Float)
    ease_after: Mapped[float] = mapped_column(Float)

    card: Mapped[Card] = relationship(back_populates="reviews")
    session: Mapped[ReviewSession] = relationship(back_populates="reviews")
