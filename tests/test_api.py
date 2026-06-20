from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from learnr.db import Base, get_session
from learnr.importer import import_csv_text
from learnr.main import app
from learnr.models import Review


def test_review_session_records_answer_timings():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    setup_session = TestingSession()
    import_csv_text(setup_session, "front,back,deck\nApfel,apple,German\n")
    setup_session.commit()
    setup_session.close()

    def override_session():
        with TestingSession() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    client = TestClient(app)
    try:
        session_payload = client.post("/api/review-sessions", json={"limit": 1}).json()
        card_id = session_payload["card"]["id"]
        review_session_id = session_payload["session"]["id"]
        shown_at = datetime(2026, 6, 13, 10, 0, 0, tzinfo=timezone.utc)
        revealed_at = datetime(2026, 6, 13, 10, 0, 2, tzinfo=timezone.utc)
        answered_at = datetime(2026, 6, 13, 10, 0, 3, tzinfo=timezone.utc)

        response = client.post(
            f"/api/review-sessions/{review_session_id}/answers",
            json={
                "card_id": card_id,
                "direction": "right",
                "shown_at": shown_at.isoformat(),
                "revealed_at": revealed_at.isoformat(),
                "answered_at": answered_at.isoformat(),
                "time_to_reveal_ms": 2000,
                "time_to_grade_ms": 1000,
            },
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
