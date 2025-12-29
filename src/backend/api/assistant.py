"""
RAG Assistant API endpoints.

Provides grounded explanations with citation requirements.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db

router = APIRouter()


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # "user" or "assistant"
    content: str


class Citation(BaseModel):
    """Citation reference for grounded responses."""
    source_type: str  # "user_document" or "reference"
    doc_id: Optional[str] = None
    doc_title: Optional[str] = None
    page: Optional[int] = None
    text_snippet: str
    relevance_score: float


class ChatRequest(BaseModel):
    """Request model for chat."""
    profile_id: str
    question: str
    
    # Context selection
    selected_analytes: Optional[list[str]] = None
    selected_panel: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    
    # Options
    include_references: bool = True  # Include general reference info
    
    # Conversation history (for context)
    history: list[ChatMessage] = []


class ResponseSegment(BaseModel):
    """
    Segment of assistant response.
    
    Separates report facts from general information.
    """
    segment_type: str  # "report_facts", "general_info", "uncertainty"
    content: str
    citations: list[Citation] = []


class ChatResponse(BaseModel):
    """Response model for chat."""
    segments: list[ResponseSegment]
    full_response: str  # Combined response text
    insufficient_context: bool = False
    insufficient_reasons: list[str] = []


class TestIntentResponse(BaseModel):
    """Response for test intent explanation."""
    analyte: str
    analyte_display_name: str
    intent_summary: str  # What the test is typically ordered for
    general_info: str  # What it helps evaluate at a high level
    citations: list[Citation]


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with the grounded assistant.
    
    Process:
    1. Retrieve relevant user document chunks
    2. Retrieve relevant reference corpus chunks
    3. Compose prompt with strict citation requirements
    4. Generate response with local LLM
    5. Validate response has required citations
    6. Return segmented response with provenance
    
    Refuses to answer if:
    - Insufficient context for grounded response
    - Question requests diagnosis/treatment advice
    - Claims cannot be supported by retrieved context
    """
    # TODO: Implement RAG pipeline with citation validation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Chat not yet implemented"
    )


@router.get("/test-intent/{analyte}", response_model=TestIntentResponse)
async def get_test_intent(
    analyte: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get explanation of what a test is typically ordered for.
    
    Provides general education about test purpose,
    grounded in curated reference corpus.
    """
    # TODO: Implement test intent lookup
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Test intent lookup not yet implemented"
    )


@router.get("/glossary/{term}")
async def get_glossary_term(
    term: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get plain-language definition of a medical term.
    
    From curated local glossary.
    """
    # TODO: Implement glossary lookup
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Glossary lookup not yet implemented"
    )
