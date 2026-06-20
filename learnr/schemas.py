from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DeckRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    direction: str
    prompt_text: str
    answer_text: str
    due_at: datetime
    review_count: int
    tags: list[str] = Field(default_factory=list)


class ReviewSessionCreate(BaseModel):
    deck_id: int | None = None
    limit: int = Field(default=20, ge=1, le=200)


class ReviewSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int | None
    target_count: int
    completed_count: int
    started_at: datetime
    completed_at: datetime | None


class ReviewAnswerCreate(BaseModel):
    card_id: int
    direction: str = Field(pattern="^(left|right)$")
    shown_at: datetime
    revealed_at: datetime | None = None
    answered_at: datetime
    time_to_reveal_ms: int | None = Field(default=None, ge=0)
    time_to_grade_ms: int | None = Field(default=None, ge=0)


class ReviewAnswerRead(BaseModel):
    session: ReviewSessionRead | None
    review_id: int
    correct: bool
    due_after: datetime
    interval_after_days: float


class SessionNextCardRead(BaseModel):
    session: ReviewSessionRead
    card: CardRead | None
    remaining: int


class ImportSummary(BaseModel):
    rows_read: int
    notes_created: int
    cards_created: int
    decks_created: int
    tags_created: int
    deck_ids: list[int]
