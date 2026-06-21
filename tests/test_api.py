from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from learnr.db import Base, get_session
from learnr.importer import import_csv_text
from learnr.main import app
from learnr.models import Card, Deck, Review


def make_test_client(csv_text: str) -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    setup_session = testing_session()
    import_csv_text(setup_session, csv_text)
    setup_session.commit()
    setup_session.close()

    def override_session() -> Iterator[Session]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), testing_session


def answer_payload(card_id: int, direction: str) -> dict[str, object]:
    shown_at = datetime(2026, 6, 13, 10, 0, 0, tzinfo=timezone.utc)
    revealed_at = datetime(2026, 6, 13, 10, 0, 2, tzinfo=timezone.utc)
    answered_at = datetime(2026, 6, 13, 10, 0, 3, tzinfo=timezone.utc)
    return {
        "card_id": card_id,
        "direction": direction,
        "shown_at": shown_at.isoformat(),
        "revealed_at": revealed_at.isoformat(),
        "answered_at": answered_at.isoformat(),
        "time_to_reveal_ms": 2000,
        "time_to_grade_ms": 1000,
    }


def set_card_state(
    testing_session: sessionmaker[Session],
    prompt_text: str,
    *,
    review_count: int,
    due_at: datetime,
) -> None:
    with testing_session() as session:
        card = session.scalar(select(Card).where(Card.prompt_text == prompt_text))
        assert card is not None
        card.state.review_count = review_count
        card.state.due_at = due_at
        session.commit()


def test_review_session_records_answer_timings():
    client, TestingSession = make_test_client("front,back,deck\nApfel,apple,German\n")
    try:
        session_payload = client.post("/api/review-sessions", json={"limit": 1}).json()
        card_id = session_payload["card"]["id"]
        review_session_id = session_payload["session"]["id"]

        response = client.post(
            f"/api/review-sessions/{review_session_id}/answers",
            json=answer_payload(card_id, "right"),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["correct"] is True
        verify_session = TestingSession()
        review = verify_session.scalar(select(Review))
        assert review is not None
        assert review.time_to_reveal_ms == 2000
        assert review.time_to_grade_ms == 1000
        assert review.correct is True
        verify_session.close()
    finally:
        app.dependency_overrides.clear()


def test_wrong_answer_does_not_complete_session_until_card_is_passed():
    client, TestingSession = make_test_client("front,back,deck\nApfel,apple,German\n")
    try:
        session_payload = client.post("/api/review-sessions", json={"limit": 1}).json()
        card_id = session_payload["card"]["id"]
        review_session_id = session_payload["session"]["id"]

        wrong_response = client.post(
            f"/api/review-sessions/{review_session_id}/answers",
            json=answer_payload(card_id, "left"),
        )

        assert wrong_response.status_code == 200
        wrong_data = wrong_response.json()
        assert wrong_data["correct"] is False
        assert wrong_data["session"]["completed_count"] == 0
        assert wrong_data["session"]["completed_at"] is None

        right_response = client.post(
            f"/api/review-sessions/{review_session_id}/answers",
            json=answer_payload(card_id, "right"),
        )

        assert right_response.status_code == 200
        right_data = right_response.json()
        assert right_data["correct"] is True
        assert right_data["session"]["completed_count"] == 1
        assert right_data["session"]["completed_at"] is not None

        verify_session = TestingSession()
        reviews = list(verify_session.scalars(select(Review).order_by(Review.id)))
        assert [review.correct for review in reviews] == [False, True]
        verify_session.close()
    finally:
        app.dependency_overrides.clear()


def test_review_session_start_returns_all_selected_cards():
    client, _ = make_test_client("front,back,deck\nApfel,apple,German\nBuch,book,German\n")
    try:
        response = client.post("/api/review-sessions", json={"limit": 2})

        assert response.status_code == 200
        data = response.json()
        assert data["session"]["target_count"] == 2
        assert len(data["cards"]) == 2
        assert data["card"] == data["cards"][0]
    finally:
        app.dependency_overrides.clear()


def test_review_session_selects_due_reviews_before_new_cards():
    client, TestingSession = make_test_client(
        "front,back,deck\nApfel,apple,German\nBuch,book,German\nHaus,house,German\n"
    )
    now = datetime.now(timezone.utc)
    set_card_state(TestingSession, "Apfel", review_count=1, due_at=now - timedelta(days=1))
    set_card_state(TestingSession, "Buch", review_count=1, due_at=now - timedelta(days=2))

    try:
        response = client.post("/api/review-sessions", json={"limit": 4})

        assert response.status_code == 200
        cards = response.json()["cards"]
        assert [card["prompt_text"] for card in cards[:2]] == ["Buch", "Apfel"]
        assert [card["review_count"] for card in cards] == [1, 1, 0, 0]
    finally:
        app.dependency_overrides.clear()


def test_review_session_pads_with_new_cards_after_due_reviews():
    client, TestingSession = make_test_client(
        "front,back,deck\nApfel,apple,German\nBuch,book,German\n"
    )
    now = datetime.now(timezone.utc)
    set_card_state(TestingSession, "Buch", review_count=1, due_at=now - timedelta(days=1))

    try:
        response = client.post("/api/review-sessions", json={"limit": 3})

        assert response.status_code == 200
        cards = response.json()["cards"]
        assert [card["prompt_text"] for card in cards] == ["Buch", "Apfel", "apple"]
        assert [card["review_count"] for card in cards] == [1, 0, 0]
    finally:
        app.dependency_overrides.clear()


def test_review_session_does_not_include_new_cards_when_due_reviews_fill_limit():
    client, TestingSession = make_test_client(
        "front,back,deck\nApfel,apple,German\nBuch,book,German\n"
    )
    now = datetime.now(timezone.utc)
    set_card_state(TestingSession, "Apfel", review_count=1, due_at=now - timedelta(days=2))
    set_card_state(TestingSession, "apple", review_count=1, due_at=now - timedelta(days=1))

    try:
        response = client.post("/api/review-sessions", json={"limit": 2})

        assert response.status_code == 200
        cards = response.json()["cards"]
        assert [card["prompt_text"] for card in cards] == ["Apfel", "apple"]
        assert [card["review_count"] for card in cards] == [1, 1]
    finally:
        app.dependency_overrides.clear()


def test_review_session_applies_deck_filter_to_reviews_and_new_cards():
    client, TestingSession = make_test_client(
        "front,back,deck\nApfel,apple,German\nLibro,book,Spanish\n"
    )
    now = datetime.now(timezone.utc)
    set_card_state(TestingSession, "Libro", review_count=1, due_at=now - timedelta(days=2))

    with TestingSession() as session:
        german_deck = session.scalar(select(Deck).where(Deck.name == "German"))
        assert german_deck is not None
        german_deck_id = german_deck.id

    try:
        response = client.post(
            "/api/review-sessions", json={"deck_id": german_deck_id, "limit": 4}
        )

        assert response.status_code == 200
        cards = response.json()["cards"]
        assert [card["prompt_text"] for card in cards] == ["Apfel", "apple"]
        assert [card["review_count"] for card in cards] == [0, 0]
    finally:
        app.dependency_overrides.clear()
