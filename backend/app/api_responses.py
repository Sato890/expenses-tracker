from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class MemberResponse(BaseModel):
    id: str
    display_name: str


class MemberListResponse(BaseModel):
    items: list[MemberResponse]


class AllocationResponse(BaseModel):
    receiver_id: str
    amount: str


class ExpenseResponse(BaseModel):
    id: str
    group_id: str
    type: Literal["expense"]
    amount: str
    currency: str
    payer_id: str
    date: date
    category_id: UUID
    allocations: list[AllocationResponse]


class ExpenseHistoryResponse(BaseModel):
    items: list[ExpenseResponse]
    limit: int
    offset: int


class MemberSettlementAmount(BaseModel):
    member_id: str
    amount: str


class SettlementAmountsResponse(BaseModel):
    group_id: str
    currency: str
    items: list[MemberSettlementAmount]


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
