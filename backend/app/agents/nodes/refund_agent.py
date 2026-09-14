"""
app/agents/nodes/refund_agent.py

Refund/Return Agent node.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import CommerceFlowState
from app.agents.tools.refund_tools import REFUND_TOOLS
from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def refund_agent_node(state: CommerceFlowState) -> CommerceFlowState:
    """Refund Agent: check return status and eligibility."""
    logger.info(f"Refund agent processing for user {state['user_id']}")

    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    user_id = state["user_id"]
    tool_results = []

    order_context = state.get("order_context") or {}
    order_number = order_context.get("order_number")

    if not settings.OPENROUTER_API_KEY or not order_number:
        if order_number:
            output = REFUND_TOOLS[0].invoke({"order_number": order_number, "user_id": user_id})
            tool_results.append({
                "tool": "get_return_status",
                "input": {"order_number": order_number},
                "output": output,
            })
        else:
            tool_results.append({
                "tool": "get_return_status",
                "input": {},
                "output": (
                    "To check your return status or initiate a return, "
                    "please provide your order number (e.g. CF-20260801-001). "
                    "You can find it in My Orders."
                ),
            })
        return {**state, "tool_results": tool_results, "selected_agent": "refund_agent"}

    try:
        api_key = settings.OPENROUTER_API_KEY
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            openai_api_key=api_key,
            openai_api_base=settings.OPENROUTER_BASE_URL,
            default_headers={"HTTP-Referer": "https://commerceflow.ai", "X-Title": "CommerceFlow AI"},
        ).bind_tools(REFUND_TOOLS)

        prompt = f"{last_human.content}\n[user_id: {user_id}]"
        if order_number:
            prompt += f"\n[order_number: {order_number}]"

        response = llm.invoke([
            SystemMessage(content="You are the Return & Refund Specialist. Always use the get_return_status tool."),
            HumanMessage(content=prompt),
        ])

        tool_map = {t.name: t for t in REFUND_TOOLS}
        if hasattr(response, "tool_calls") and response.tool_calls:
            for tc in response.tool_calls:
                args = tc.get("args", {})
                args.setdefault("user_id", user_id)
                tool_func = tool_map.get(tc["name"])
                if tool_func:
                    output = tool_func.invoke(args)
                    tool_results.append({"tool": tc["name"], "input": args, "output": output})

        if not tool_results and order_number:
            output = REFUND_TOOLS[0].invoke({"order_number": order_number, "user_id": user_id})
            tool_results.append({"tool": "get_return_status", "input": {}, "output": output})

    except Exception as e:
        logger.error(f"Refund agent failed: {e}", exc_info=True)
        if order_number:
            output = REFUND_TOOLS[0].invoke({"order_number": order_number, "user_id": user_id})
            tool_results.append({"tool": "get_return_status", "input": {}, "output": output})

    return {**state, "tool_results": tool_results, "selected_agent": "refund_agent"}
