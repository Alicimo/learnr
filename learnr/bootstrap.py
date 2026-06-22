from importlib import resources

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from learnr.importer import import_csv_text
from learnr.models import Card, Deck, Note

STARTER_DECK_PACKAGE = "learnr.starter_decks"
GOETHE_A1_CSV = "goethe_a1_wordlist.csv"


def has_learning_content(session: Session) -> bool:
    return any(
        session.scalar(select(exists().select_from(model)))
        for model in (Deck, Note, Card)
    )


def seed_starter_decks_if_empty(session: Session) -> bool:
    if has_learning_content(session):
        return False

    csv_text = resources.files(STARTER_DECK_PACKAGE).joinpath(GOETHE_A1_CSV).read_text()
    import_csv_text(session, csv_text)
    session.commit()
    return True
