import csv
from dataclasses import dataclass, field
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from learnr.models import Card, CardState, Deck, Note, Tag, utc_now


DEFAULT_DECK_NAME = "Imported"


@dataclass
class ImportSummaryData:
    rows_read: int = 0
    notes_created: int = 0
    cards_created: int = 0
    decks_created: int = 0
    tags_created: int = 0
    deck_ids: set[int] = field(default_factory=set)


def normalize_text(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def split_tags(value: str | None) -> list[str]:
    if not value:
        return []
    raw_tags = value.replace(",", ";").split(";")
    return [tag.strip() for tag in raw_tags if tag.strip()]


def get_or_create_deck(session: Session, name: str, summary: ImportSummaryData) -> Deck:
    clean_name = name.strip() or DEFAULT_DECK_NAME
    deck = session.scalar(select(Deck).where(Deck.name == clean_name))
    if deck:
        return deck
    deck = Deck(name=clean_name)
    session.add(deck)
    session.flush()
    summary.decks_created += 1
    return deck


def get_or_create_tag(session: Session, name: str, summary: ImportSummaryData) -> Tag:
    clean_name = name.strip()
    tag = session.scalar(select(Tag).where(Tag.name == clean_name))
    if tag:
        return tag
    tag = Tag(name=clean_name)
    session.add(tag)
    session.flush()
    summary.tags_created += 1
    return tag


def get_or_create_note(
    session: Session,
    front: str,
    back: str,
    source_language: str | None,
    target_language: str | None,
    summary: ImportSummaryData,
) -> Note:
    normalized_source = normalize_text(front)
    normalized_target = normalize_text(back)
    note = session.scalar(
        select(Note).where(
            Note.normalized_source == normalized_source,
            Note.normalized_target == normalized_target,
            Note.source_language == source_language,
            Note.target_language == target_language,
        )
    )
    if note:
        return note
    note = Note(
        source_text=front.strip(),
        target_text=back.strip(),
        normalized_source=normalized_source,
        normalized_target=normalized_target,
        source_language=source_language,
        target_language=target_language,
    )
    session.add(note)
    session.flush()
    summary.notes_created += 1
    return note


def get_or_create_card(
    session: Session,
    note: Note,
    direction: str,
    prompt: str,
    answer: str,
    summary: ImportSummaryData,
) -> Card:
    normalized_prompt = normalize_text(prompt)
    normalized_answer = normalize_text(answer)
    card = session.scalar(
        select(Card).where(
            Card.normalized_prompt == normalized_prompt,
            Card.normalized_answer == normalized_answer,
            Card.direction == direction,
        )
    )
    if card:
        return card
    card = Card(
        note=note,
        direction=direction,
        prompt_text=prompt.strip(),
        answer_text=answer.strip(),
        normalized_prompt=normalized_prompt,
        normalized_answer=normalized_answer,
        state=CardState(due_at=utc_now()),
    )
    session.add(card)
    session.flush()
    summary.cards_created += 1
    return card


def import_csv_text(session: Session, csv_text: str, fallback_deck_name: str | None = None) -> ImportSummaryData:
    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("CSV must include a header row.")

    fieldnames = {field.strip().casefold() for field in reader.fieldnames}
    missing = {"front", "back"} - fieldnames
    if missing:
        raise ValueError("CSV must include front and back columns.")

    summary = ImportSummaryData()

    for raw_row in reader:
        row = {key.strip().casefold(): (value or "").strip() for key, value in raw_row.items() if key}
        front = row.get("front", "")
        back = row.get("back", "")
        if not front or not back:
            continue

        summary.rows_read += 1
        deck_name = row.get("deck") or fallback_deck_name or DEFAULT_DECK_NAME
        deck = get_or_create_deck(session, deck_name, summary)
        summary.deck_ids.add(deck.id)

        tags = [get_or_create_tag(session, tag_name, summary) for tag_name in split_tags(row.get("tags"))]
        source_language = row.get("source_language") or None
        target_language = row.get("target_language") or None

        note = get_or_create_note(session, front, back, source_language, target_language, summary)
        cards = [
            get_or_create_card(session, note, "forward", front, back, summary),
            get_or_create_card(session, note, "reverse", back, front, summary),
        ]
        for card in cards:
            if deck not in card.decks:
                card.decks.append(deck)
            for tag in tags:
                if tag not in card.tags:
                    card.tags.append(tag)

    return summary
