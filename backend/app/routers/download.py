"""A complete, internally consistent group copy for offline clients."""

import base64
import gzip
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.adapters.orm import expenses, groups
from app.api_errors import error_response
from app.database import get_session
from app.domain.group import Group
from app.routers.expenses import ExpenseResponse, expense_response
from app.routers.members import MemberResponse
from app.routers.settlement_amounts import (
    MemberSettlementAmount,
    SettlementAmountsResponse,
)

router = APIRouter()
DOWNLOAD_FORMAT_VERSION = 1


class DownloadGroup(BaseModel):
    id: str
    name: str


class DownloadCategory(BaseModel):
    id: str
    name: str


class GroupDownloadResponse(BaseModel):
    group: DownloadGroup
    members: list[MemberResponse]
    categories: list[DownloadCategory]
    transactions: list[ExpenseResponse]
    settlement_amounts: SettlementAmountsResponse
    transaction_count: int
    sync_token: str


def _sync_token(group_id: str, revision: int) -> str:
    """Keep the representation version opaque to the Android client."""
    value = f"v{DOWNLOAD_FORMAT_VERSION}:{group_id}:{revision}".encode()
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _matches_etag(header: str | None, etag: str) -> bool:
    if header is None:
        return False
    return any(
        candidate.strip().removeprefix("W/") in (etag, "*")
        for candidate in header.split(",")
    )


def _download_body(group: Group, count: int, token: str) -> GroupDownloadResponse:
    transactions = [
        expense_response(group.id, expense) for expense in group.transactions
    ]
    categories = {
        expense.category.id: DownloadCategory(
            id=str(expense.category.id), name=expense.category.name
        )
        for expense in group.transactions
    }
    amounts = group.calculate_member_settlement_amounts()
    return GroupDownloadResponse(
        group=DownloadGroup(id=group.id, name=group.name),
        members=[
            MemberResponse(id=member.id, display_name=member.name)
            for member in group.members
        ],
        categories=[categories[key] for key in sorted(categories)],
        transactions=transactions,
        settlement_amounts=SettlementAmountsResponse(
            group_id=group.id,
            currency="EUR",
            items=[
                MemberSettlementAmount(member_id=member.id, amount=str(amount.amount))
                for member, amount in sorted(
                    amounts.items(), key=lambda item: item[0].id
                )
            ],
        ),
        transaction_count=count,
        sync_token=token,
    )


@router.get("/groups/{group_id}/download", response_model=GroupDownloadResponse)
def download_group(
    group_id: str,
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> Response:
    # This must be the first SQL statement in this request's transaction.
    with session.begin():
        session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        )
        row = session.execute(
            select(groups.c.id, groups.c.revision).where(groups.c.id == group_id)
        ).one_or_none()
        if row is None:
            return error_response(404, "GROUP_NOT_FOUND", "Group not found.")

        token = _sync_token(group_id, row.revision)
        etag = f'"{token}"'
        if _matches_etag(request.headers.get("if-none-match"), etag):
            return Response(status_code=304, headers={"ETag": etag})

        count = session.scalar(
            select(func.count())
            .select_from(expenses)
            .where(expenses.c.group_id == group_id)
        )
        group = session.get(Group, group_id)
        assert group is not None
        body = _download_body(group, count, token)
        content = json.dumps(
            body.model_dump(mode="json"), separators=(",", ":")
        ).encode()

    headers = {"ETag": etag, "Vary": "Accept-Encoding"}
    if "gzip" in request.headers.get("accept-encoding", "").lower():
        content = gzip.compress(content)
        headers["Content-Encoding"] = "gzip"
    return Response(content=content, media_type="application/json", headers=headers)
