from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from learnr.db import Base
from learnr.importer import import_csv_text
from learnr.models import Card, Deck, Note


def make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()


def test_csv_import_creates_bidirectional_cards_and_deck_membership():
    session = make_session()
    summary = import_csv_text(
        session,
        "front,back,deck,tags,source_language,target_language\nApfel,apple,German,noun;food,de,en\n",
    )
    session.commit()

    assert summary.rows_read == 1
    assert summary.notes_created == 1
    assert summary.cards_created == 2
    assert len(list(session.scalars(select(Note)))) == 1
    cards = list(session.scalars(select(Card)))
    deck = session.scalar(select(Deck).where(Deck.name == "German"))
    assert deck is not None
    assert {card.direction for card in cards} == {"forward", "reverse"}
    assert all(deck in card.decks for card in cards)
    assert all(card.state is not None for card in cards)


def test_csv_import_deduplicates_cards_across_decks():
    session = make_session()
    import_csv_text(session, "front,back,deck\nApfel,apple,German A1\n")
    import_csv_text(session, "front,back,deck\nApfel,apple,German Basics\n")
    session.commit()

    cards = list(session.scalars(select(Card)))
    decks = list(session.scalars(select(Deck)))
    assert len(cards) == 2
    assert len(decks) == 2
    assert all(len(card.decks) == 2 for card in cards)
