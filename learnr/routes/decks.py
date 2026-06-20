from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from learnr.db import get_session
from learnr.models import Deck
from learnr.schemas import DeckRead

router = APIRouter(prefix="/api/decks", tags=["decks"])


@router.get("", response_model=list[DeckRead])
def list_decks(db: Session = Depends(get_session)) -> list[Deck]:
    return list(db.scalars(select(Deck).order_by(Deck.name)))
