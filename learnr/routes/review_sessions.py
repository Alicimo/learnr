from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from learnr.db import get_session
from learnr.models import Card, Deck, Review, ReviewSession, utc_now
from learnr.review_queries import due_cards_query, to_card_read, to_session_read
from learnr.scheduler import schedule_binary
from learnr.schemas import (
    ReviewAnswerCreate,
    ReviewAnswerRead,
    ReviewSessionCreate,
    SessionNextCardRead,
)

router = APIRouter(prefix="/api/review-sessions", tags=["review sessions"])


@router.post("", response_model=SessionNextCardRead)
def create_review_session(payload: ReviewSessionCreate, db: Session = Depends(get_session)) -> SessionNextCardRead:
    if payload.deck_id is not None and db.get(Deck, payload.deck_id) is None:
        raise HTTPException(status_code=404, detail="Deck not found.")

    due_cards = list(db.scalars(due_cards_query(payload.deck_id).limit(payload.limit)))
    review_session = ReviewSession(deck_id=payload.deck_id, target_count=len(due_cards))
    db.add(review_session)
    db.commit()
    db.refresh(review_session)

    return SessionNextCardRead(
        session=to_session_read(review_session),
        card=to_card_read(due_cards[0]) if due_cards else None,
        remaining=len(due_cards),
    )


@router.get("/{session_id}/next", response_model=SessionNextCardRead)
def get_next_card(session_id: int, db: Session = Depends(get_session)) -> SessionNextCardRead:
    review_session = db.get(ReviewSession, session_id)
    if review_session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    if review_session.completed_count >= review_session.target_count:
        if review_session.completed_at is None:
            review_session.completed_at = utc_now()
            db.commit()
            db.refresh(review_session)
        return SessionNextCardRead(session=to_session_read(review_session), card=None, remaining=0)

    card = db.scalars(due_cards_query(review_session.deck_id).limit(1)).first()
    remaining = max(0, review_session.target_count - review_session.completed_count)
    return SessionNextCardRead(
        session=to_session_read(review_session),
        card=to_card_read(card) if card else None,
        remaining=remaining if card else 0,
    )


@router.post("/{session_id}/answers", response_model=ReviewAnswerRead)
def answer_card(
    session_id: int,
    payload: ReviewAnswerCreate,
    db: Session = Depends(get_session),
) -> ReviewAnswerRead:
    review_session = db.get(ReviewSession, session_id)
    if review_session is None:
        raise HTTPException(status_code=404, detail="Session not found.")

    card = db.scalar(
        select(Card)
        .options(selectinload(Card.state))
        .where(Card.id == payload.card_id)
    )
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found.")
    if card.state is None:
        raise HTTPException(status_code=409, detail="Card has no scheduling state.")

    correct = payload.direction == "right"
    answered_at = payload.answered_at.astimezone(timezone.utc)
    due_before = card.state.due_at
    interval_before = card.state.interval_days
    ease_before = card.state.ease_factor
    scheduled = schedule_binary(card.state, correct, answered_at)

    card.state.due_at = scheduled.due_at
    card.state.interval_days = scheduled.interval_days
    card.state.ease_factor = scheduled.ease_factor
    card.state.review_count = scheduled.review_count
    card.state.lapse_count = scheduled.lapse_count
    card.state.stability = scheduled.stability
    card.state.difficulty = scheduled.difficulty
    card.state.last_reviewed_at = answered_at

    review = Review(
        card_id=card.id,
        deck_id=review_session.deck_id,
        session_id=review_session.id,
        shown_at=payload.shown_at.astimezone(timezone.utc),
        revealed_at=payload.revealed_at.astimezone(timezone.utc) if payload.revealed_at else None,
        answered_at=answered_at,
        time_to_reveal_ms=payload.time_to_reveal_ms,
        time_to_grade_ms=payload.time_to_grade_ms,
        direction=payload.direction,
        correct=correct,
        due_before=due_before,
        due_after=scheduled.due_at,
        interval_before_days=interval_before,
        interval_after_days=scheduled.interval_days,
        ease_before=ease_before,
        ease_after=scheduled.ease_factor,
    )
    db.add(review)
    review_session.completed_count += 1
    if review_session.completed_count >= review_session.target_count:
        review_session.completed_at = utc_now()

    db.commit()
    db.refresh(review)
    db.refresh(review_session)
    return ReviewAnswerRead(
        session=to_session_read(review_session),
        review_id=review.id,
        correct=correct,
        due_after=scheduled.due_at,
        interval_after_days=scheduled.interval_days,
    )
