from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from learnr.bootstrap import seed_starter_decks_if_empty
from learnr.db import Base
from learnr.importer import import_csv_text
from learnr.models import Card, Deck, Note


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return testing_session()


def count_rows(session: Session, model: type[object]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_seed_starter_decks_imports_goethe_a1_for_empty_database() -> None:
    session = make_session()

    seeded = seed_starter_decks_if_empty(session)

    assert seeded is True
    deck = session.scalar(select(Deck).where(Deck.name == "Goethe A1"))
    assert deck is not None
    assert count_rows(session, Note) == 740
    assert count_rows(session, Card) == 1480


def test_seed_starter_decks_is_idempotent() -> None:
    session = make_session()

    assert seed_starter_decks_if_empty(session) is True
    deck_count = count_rows(session, Deck)
    note_count = count_rows(session, Note)
    card_count = count_rows(session, Card)

    assert seed_starter_decks_if_empty(session) is False
    assert count_rows(session, Deck) == deck_count
    assert count_rows(session, Note) == note_count
    assert count_rows(session, Card) == card_count


def test_seed_starter_decks_skips_existing_learning_content() -> None:
    session = make_session()
    import_csv_text(session, "front,back,deck\nApfel,apple,Personal\n")
    session.commit()

    seeded = seed_starter_decks_if_empty(session)

    assert seeded is False
    assert session.scalar(select(Deck).where(Deck.name == "Goethe A1")) is None
    assert count_rows(session, Deck) == 1
    assert count_rows(session, Note) == 1
    assert count_rows(session, Card) == 2
