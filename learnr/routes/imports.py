from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from learnr.db import get_session
from learnr.importer import import_csv_text
from learnr.schemas import ImportSummary

router = APIRouter(prefix="/api/import", tags=["imports"])

CSV_CONTENT_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "text/plain",
    "application/octet-stream",
}


@router.post("/csv", response_model=ImportSummary)
async def import_csv(
    file: UploadFile = File(...),
    deck_name: str | None = Form(default=None),
    db: Session = Depends(get_session),
) -> ImportSummary:
    if file.content_type not in CSV_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Upload a CSV file.")
    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
        summary = import_csv_text(db, text, deck_name)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    return ImportSummary(
        rows_read=summary.rows_read,
        notes_created=summary.notes_created,
        cards_created=summary.cards_created,
        decks_created=summary.decks_created,
        tags_created=summary.tags_created,
        deck_ids=sorted(summary.deck_ids),
    )
