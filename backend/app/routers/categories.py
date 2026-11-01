from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.orm import categories
from app.database import get_session

router = APIRouter()


@router.get("/categories")
def list_categories(
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, list[dict[str, str]]]:
    return {
        "items": [
            {"id": str(row.id), "name": row.name}
            for row in session.execute(
                select(categories.c.id, categories.c.name).order_by(categories.c.name)
            ).all()
        ]
    }
