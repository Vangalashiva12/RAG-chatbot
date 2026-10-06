from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User


router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"]
)


# ============================================================
# Request Schemas
# ============================================================

class ConversationCreate(BaseModel):
    title: str = "New Conversation"


# ============================================================
# Response Schemas
# ============================================================

class ConversationResponse(BaseModel):
    id: int
    title: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str

    class Config:
        from_attributes = True


class ConversationDetailResponse(BaseModel):
    id: int
    title: str
    messages: list[MessageResponse]

    class Config:
        from_attributes = True


class ConversationMessagesResponse(BaseModel):
    conversation_id: int
    messages: list[MessageResponse]

    class Config:
        from_attributes = True


# ============================================================
# Create Conversation
# ============================================================

@router.post(
    "/",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED
)
def create_conversation(
    request: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = Conversation(
        user_id=current_user.id,
        title=request.title
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


# ============================================================
# List User's Conversations
# ============================================================

@router.get(
    "/",
    response_model=list[ConversationResponse]
)
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversations = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == current_user.id
        )
        .order_by(
            Conversation.updated_at.desc()
        )
        .all()
    )

    return conversations


# ============================================================
# Get All Messages for a Conversation
# ============================================================

@router.get(
    "/{conversation_id}/messages",
    response_model=ConversationMessagesResponse
)
def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Make sure the conversation belongs to the logged-in user
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Get all messages in chronological order
    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation.id
        )
        .order_by(
            Message.created_at.asc()
        )
        .all()
    )

    return ConversationMessagesResponse(
        conversation_id=conversation.id,
        messages=messages
    )


# ============================================================
# Get Conversation with Messages
# ============================================================

@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse
)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return conversation


# ============================================================
# Delete Conversation
# ============================================================

@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    db.delete(conversation)
    db.commit()