from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from learnr.models import Card, CardState, ReviewSession, card_decks, utc_now
from learnr.schemas import CardRead, ReviewSessionRead


def to_session_read(session: ReviewSession) -> ReviewSessionRead:
    return ReviewSessionRead.model_validate(session)


def to_card_read(card: Card) -> CardRead:
    return CardRead(
        id=card.id,
        direction=card.direction,
        prompt_text=card.prompt_text,
        answer_text=card.answer_text,
        due_at=card.state.due_at,
        review_count=card.state.review_count,
        tags=sorted(tag.name for tag in card.tags),
    )


def _card_query(deck_id: int | None = None) -> Select[tuple[Card]]:
    stmt = (
        select(Card)
        .join(CardState)
        .options(selectinload(Card.state), selectinload(Card.tags))
    )
    if deck_id is not None:
        stmt = stmt.join(card_decks).where(card_decks.c.deck_id == deck_id)
    return stmt


def due_review_cards_query(deck_id: int | None = None) -> Select[tuple[Card]]:
    return (
        _card_query(deck_id)
        .where(CardState.review_count > 0, CardState.due_at <= utc_now())
        .order_by(CardState.due_at.asc(), Card.id.asc())
    )


def new_cards_query(deck_id: int | None = None) -> Select[tuple[Card]]:
    return _card_query(deck_id).where(CardState.review_count == 0).order_by(Card.id.asc())


def due_cards_query(deck_id: int | None = None) -> Select[tuple[Card]]:
    stmt = (
        select(Card)
        .join(CardState)
        .options(selectinload(Card.state), selectinload(Card.tags))
        .where(CardState.due_at <= utc_now())
        .order_by(CardState.due_at.asc(), Card.id.asc())
    )
    if deck_id is not None:
        stmt = stmt.join(card_decks).where(card_decks.c.deck_id == deck_id)
    return stmt
