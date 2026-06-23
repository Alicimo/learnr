from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from learnr.db import get_session
from learnr.models import Card, CardState, Deck, card_decks, utc_now
from learnr.schemas import DeckRead, DeckSummary, DeckSummaryRead

router = APIRouter(prefix="/api/decks", tags=["decks"])


@router.get("", response_model=list[DeckRead])
def list_decks(db: Session = Depends(get_session)) -> list[Deck]:
    return list(db.scalars(select(Deck).order_by(Deck.name)))


def _int_count(value: int | None) -> int:
    return int(value or 0)


def _summary_from_counts(
    *,
    deck_id: int | None,
    name: str,
    total_cards: int | None,
    reviewed_cards: int | None,
    due_review_cards: int | None,
    new_cards: int | None,
    due_forward_cards: int | None,
    due_reverse_cards: int | None,
) -> DeckSummary:
    return DeckSummary(
        id=deck_id,
        name=name,
        total_cards=_int_count(total_cards),
        reviewed_cards=_int_count(reviewed_cards),
        due_review_cards=_int_count(due_review_cards),
        new_cards=_int_count(new_cards),
        due_forward_cards=_int_count(due_forward_cards),
        due_reverse_cards=_int_count(due_reverse_cards),
    )


def _summary_columns() -> tuple[object, ...]:
    now = utc_now()
    due_review = (CardState.review_count > 0) & (CardState.due_at <= now)
    return (
        func.count(Card.id),
        func.sum(case((CardState.review_count > 0, 1), else_=0)),
        func.sum(case((due_review, 1), else_=0)),
        func.sum(case((CardState.review_count == 0, 1), else_=0)),
        func.sum(case((due_review & (Card.direction == "forward"), 1), else_=0)),
        func.sum(case((due_review & (Card.direction == "reverse"), 1), else_=0)),
    )


@router.get("/summary", response_model=DeckSummaryRead)
def deck_summary(db: Session = Depends(get_session)) -> DeckSummaryRead:
    total_row = db.execute(select(*_summary_columns()).select_from(Card).join(CardState)).one()
    total = _summary_from_counts(
        deck_id=None,
        name="All Decks",
        total_cards=total_row[0],
        reviewed_cards=total_row[1],
        due_review_cards=total_row[2],
        new_cards=total_row[3],
        due_forward_cards=total_row[4],
        due_reverse_cards=total_row[5],
    )

    deck_rows = db.execute(
        select(Deck.id, Deck.name, *_summary_columns())
        .select_from(Deck)
        .outerjoin(card_decks, card_decks.c.deck_id == Deck.id)
        .outerjoin(Card, Card.id == card_decks.c.card_id)
        .outerjoin(CardState, CardState.card_id == Card.id)
        .group_by(Deck.id)
        .order_by(Deck.name)
    )
    decks = [
        _summary_from_counts(
            deck_id=row[0],
            name=row[1],
            total_cards=row[2],
            reviewed_cards=row[3],
            due_review_cards=row[4],
            new_cards=row[5],
            due_forward_cards=row[6],
            due_reverse_cards=row[7],
        )
        for row in deck_rows
    ]
    return DeckSummaryRead(total=total, decks=decks)
