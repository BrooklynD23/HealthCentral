"""
Memory store CRUD API endpoints.

ASSIST-MEM-001: Per-profile persistent memory items for the assistant.
All endpoints require authentication and enforce profile isolation.
"""

import logging
import re
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func

from core.auth import RequireAuth, ProfileDbSession
from core.config import settings
from models.memory_item import MemoryItem

logger = logging.getLogger(__name__)

router = APIRouter()

# UUID validation pattern
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _validate_uuid(value: str, field_name: str = "ID") -> str:
    if not UUID_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format",
        )
    return value


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class MemoryItemCreate(BaseModel):
    """Request model for creating a memory item."""
    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1, max_length=10_000)
    category: Optional[str] = Field(None, max_length=100)


class MemoryItemUpdate(BaseModel):
    """Request model for updating a memory item."""
    key: Optional[str] = Field(None, min_length=1, max_length=255)
    value: Optional[str] = Field(None, min_length=1, max_length=10_000)
    category: Optional[str] = Field(None, max_length=100)


class MemoryItemResponse(BaseModel):
    """Response model for memory item."""
    id: str
    profile_id: str
    key: str
    value: str
    category: Optional[str] = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, item: MemoryItem) -> "MemoryItemResponse":
        return cls(
            id=item.id,
            profile_id=item.profile_id,
            key=item.key,
            value=item.value,
            category=item.category,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=MemoryItemResponse, status_code=status.HTTP_201_CREATED)
async def create_memory_item(
    data: MemoryItemCreate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Create a new memory item for the authenticated profile."""
    profile_id = session.profile_id

    # Enforce per-profile limit
    count_result = await profile_db.execute(
        select(func.count(MemoryItem.id)).where(
            MemoryItem.profile_id == profile_id
        )
    )
    current_count = count_result.scalar() or 0

    if current_count >= settings.max_memory_items_per_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Memory item limit reached ({settings.max_memory_items_per_profile})",
        )

    item = MemoryItem(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        key=data.key,
        value=data.value,
        category=data.category,
    )
    profile_db.add(item)
    await profile_db.commit()
    await profile_db.refresh(item)

    return MemoryItemResponse.from_model(item)


@router.get("/", response_model=list[MemoryItemResponse])
async def list_memory_items(
    session: RequireAuth,
    category: Optional[str] = Query(None, description="Filter by category"),
    profile_db: ProfileDbSession = None,
):
    """List memory items for the authenticated profile."""
    profile_id = session.profile_id

    query = select(MemoryItem).where(MemoryItem.profile_id == profile_id)
    if category:
        query = query.where(MemoryItem.category == category)
    query = query.order_by(MemoryItem.updated_at.desc())

    result = await profile_db.execute(query)
    items = result.scalars().all()

    return [MemoryItemResponse.from_model(item) for item in items]


@router.get("/{item_id}", response_model=MemoryItemResponse)
async def get_memory_item(
    item_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Get a specific memory item by ID."""
    _validate_uuid(item_id, "item_id")
    profile_id = session.profile_id

    result = await profile_db.execute(
        select(MemoryItem).where(
            MemoryItem.id == item_id,
            MemoryItem.profile_id == profile_id,
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory item not found",
        )

    return MemoryItemResponse.from_model(item)


@router.put("/{item_id}", response_model=MemoryItemResponse)
async def update_memory_item(
    item_id: str,
    data: MemoryItemUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Update a memory item."""
    _validate_uuid(item_id, "item_id")
    profile_id = session.profile_id

    result = await profile_db.execute(
        select(MemoryItem).where(
            MemoryItem.id == item_id,
            MemoryItem.profile_id == profile_id,
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory item not found",
        )

    if data.key is not None:
        item.key = data.key
    if data.value is not None:
        item.value = data.value
    if data.category is not None:
        item.category = data.category

    await profile_db.commit()
    await profile_db.refresh(item)

    return MemoryItemResponse.from_model(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_item(
    item_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Delete a memory item."""
    _validate_uuid(item_id, "item_id")
    profile_id = session.profile_id

    result = await profile_db.execute(
        select(MemoryItem).where(
            MemoryItem.id == item_id,
            MemoryItem.profile_id == profile_id,
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory item not found",
        )

    await profile_db.delete(item)
    await profile_db.commit()
