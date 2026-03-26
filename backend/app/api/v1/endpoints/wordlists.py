"""Wordlist management endpoints"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.wordlist_manager import WordlistManager
from app.api.deps import get_current_user, get_db
from app.models.user import User

router = APIRouter()
_manager = WordlistManager()


class CustomWordlistCreate(BaseModel):
    name: str
    words: List[str]


class WordlistEntry(BaseModel):
    name: str
    path: str
    type: str
    available: Optional[bool] = None
    size_bytes: Optional[int] = None
    word_count: Optional[int] = None


class WordlistListResponse(BaseModel):
    system: List[WordlistEntry]
    custom: List[WordlistEntry]


@router.get("/wordlists", response_model=WordlistListResponse)
def list_wordlists(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all available wordlists (system + custom)."""
    data = _manager.list_all()
    return WordlistListResponse(
        system=[WordlistEntry(**w) for w in data["system"]],
        custom=[WordlistEntry(**w) for w in data["custom"]],
    )


@router.post("/wordlists/custom", status_code=status.HTTP_201_CREATED)
def create_custom_wordlist(
    payload: CustomWordlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a custom wordlist from a list of words."""
    if not payload.words:
        raise HTTPException(status_code=400, detail="words list cannot be empty")
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="name cannot be empty")

    path = _manager.save_custom_wordlist(payload.name, payload.words)
    return {
        "name": payload.name,
        "path": path,
        "word_count": len(payload.words),
        "type": "custom",
    }


@router.delete("/wordlists/custom/{name}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_wordlist(
    name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a custom wordlist by name."""
    deleted = _manager.delete_custom_wordlist(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Wordlist '{name}' not found")
