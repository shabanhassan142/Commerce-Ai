"""
app/api/v1/endpoints/chat.py

Chat endpoint triggering the LangGraph multi-agent customer support flow.
"""

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.models.user import User
from app.services.chat_service import ChatService
from app.utils.responses import error_response, success_response

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="Customer message text")
    conversation_id: str | None = Field(None, description="Optional existing conversation UUID")
    product_id: str | None = Field(None, description="Optional product UUID from ProductDetail page — provides product context")



@router.post(
    "",
    summary="Send a message to the AI customer support multi-agent system",
    status_code=status.HTTP_200_OK,
)
async def chat_with_agent(
    payload: ChatRequest,
    user: User = Depends(get_current_active_user),
):
    """
    Main Chat API Endpoint.

    Flow:
    - User message is received with optional conversation_id.
    - Router executes the LangGraph stateful graph (Supervisor -> Specialist Agent -> Tools -> Response Agent).
    - Checks confidence and executes escalation if needed.
    - Saves conversation state & history.
    - Returns structured answer with intent, agent info, citations, and ticket references.
    """
    try:
        result = ChatService.process_message(
            user_id=str(user.id),
            message=payload.message,
            conversation_id=payload.conversation_id,
            product_id=payload.product_id,
        )

        return success_response(
            data=result,
            message="Agent response generated successfully",
        )
    except Exception as e:
        return error_response(
            message=f"Chat processing failed: {str(e)}",
            status_code=500,
        )
