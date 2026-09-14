"""
app/services/chat_service.py

Orchestrates the LangGraph multi-agent flow and conversation memory persistence.

Production hardening (Module 7):
  - graph.invoke() is wrapped with a 60-second thread timeout.
  - LLM failures and agent errors are caught and return a graceful degradation message.
  - Internal exception details are never exposed in the response payload.
"""

from __future__ import annotations

import concurrent.futures
from typing import Any

from langchain_core.messages import HumanMessage

from app.agents.graph import get_commerce_graph
from app.agents.memory import (
    create_conversation,
    load_conversation_history,
    save_conversation_turn,
)
from app.agents.state import initial_state
from app.core.logging import get_logger

logger = get_logger(__name__)

# Maximum seconds to wait for the LangGraph agent to respond.
# If the LLM or a tool call exceeds this, return a graceful fallback.
_AGENT_TIMEOUT_SECONDS = 60

_TIMEOUT_MESSAGE = (
    "I'm sorry, the AI assistant is taking longer than expected to respond. "
    "Please try again in a moment, or contact our support team directly."
)

_ERROR_MESSAGE = (
    "I'm sorry, I encountered an issue processing your request. "
    "Please try again or contact our support team if the problem persists."
)


class ChatService:
    """Service layer handling multi-agent execution and chat history."""

    @staticmethod
    def process_message(
        user_id: str,
        message: str,
        conversation_id: str | None = None,
        product_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a user message through the LangGraph agent system.

        Args:
            user_id: The authenticated user's ID
            message: Customer's input message text
            conversation_id: Optional existing conversation ID

        Returns:
            Structured dict containing final answer, metadata, citations, etc.
            Never raises — returns a graceful error message on failure.
        """
        # 1. Ensure conversation ID exists
        if not conversation_id:
            conversation_id = create_conversation(user_id)

        # 2. Load past conversation history
        history = load_conversation_history(conversation_id)

        # 3. Append current user message
        messages = list(history) + [HumanMessage(content=message)]

        # 4. Prepare initial state
        state = initial_state(
            conversation_id=conversation_id,
            user_id=user_id,
            messages=messages,
            product_id_from_detail=product_id,
        )

        # 5. Execute LangGraph workflow with timeout
        #    Uses a thread executor so we can apply a wall-clock timeout.
        #    The graph runs synchronously inside the thread.
        response_text = _ERROR_MESSAGE
        intent = "unknown"
        agent = "unknown"
        confidence = 0.0
        tool_results: list = []
        citations: list = []
        ticket_id = None
        timed_out = False

        try:
            graph = get_commerce_graph()

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(graph.invoke, state)
                try:
                    final_state = future.result(timeout=_AGENT_TIMEOUT_SECONDS)
                except concurrent.futures.TimeoutError:
                    timed_out = True
                    logger.error(
                        f"LangGraph timeout after {_AGENT_TIMEOUT_SECONDS}s "
                        f"for conversation {conversation_id}"
                    )
                    response_text = _TIMEOUT_MESSAGE
                else:
                    # Extract results from completed state
                    response_text = final_state.get("response", _ERROR_MESSAGE)
                    intent = final_state.get("intent", "unknown")
                    agent = final_state.get("selected_agent", "unknown")
                    confidence = final_state.get("confidence", 0.0)
                    tool_results = final_state.get("tool_results", [])
                    citations = final_state.get("citations", [])
                    ticket_id = final_state.get("ticket_id")

        except Exception as exc:
            # Log with full traceback internally, return clean message to user
            logger.error(
                f"LangGraph agent error for conversation {conversation_id}: "
                f"{type(exc).__name__}",
                exc_info=True,
            )
            response_text = _ERROR_MESSAGE
            intent = "error"
            agent = "error"

        # 6. Persist turn to DB (even on error/timeout, so the conversation is recorded)
        try:
            save_conversation_turn(
                conversation_id=conversation_id,
                user_id=user_id,
                human_message=message,
                ai_message=response_text,
                intent=intent,
                agent=agent,
                confidence=confidence,
                tool_results=tool_results,
                ticket_id=ticket_id,
            )
        except Exception as persist_exc:
            logger.error(
                f"Failed to persist conversation turn {conversation_id}: {persist_exc}",
                exc_info=True,
            )

        return {
            "conversation_id": conversation_id,
            "answer": response_text,
            "message": response_text,
            "intent": intent,
            "agent": agent,
            "confidence": confidence,
            "citations": citations,
            "ticket_id": ticket_id,
            "tool_calls_count": len(tool_results),
            "timed_out": timed_out,
        }
