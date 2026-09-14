"""
app/agents/nodes/order_agent.py

Order Agent node — handles order status, tracking, and history queries.
Uses tool-calling with ORDER_TOOLS.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from app.agents.state import CommerceFlowState
from app.agents.tools.order_tools import ORDER_TOOLS
from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

ORDER_AGENT_PROMPT = """You are the Order Specialist for CommerceFlow AI.

Your role: Answer questions about orders — status, tracking, delivery, order history, and order details.

You have access to these tools:
- get_order_status: Get full details of a specific order by its order number
- list_recent_orders: List the customer's most recent orders

Guidelines:
- Always use tools to fetch real data — never guess order details.
- Be specific and factual with order information.
- If the customer provides an order number, always use get_order_status first.
- If no order number is given, use list_recent_orders to show recent orders.
- Be helpful and empathetic about delays or issues.

The user_id for database queries is available in the tool calls — use it exactly as provided.
"""


def _get_llm_with_tools():
    api_key = settings.OPENROUTER_API_KEY or "no-key"
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        openai_api_key=api_key,
        openai_api_base=settings.OPENROUTER_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://commerceflow.ai",
            "X-Title": "CommerceFlow AI",
        },
    )
    return llm.bind_tools(ORDER_TOOLS)


def order_agent_node(state: CommerceFlowState) -> CommerceFlowState:
    """Order Agent: fetch order data via tools and prepare tool_results."""
    logger.info(f"Order agent processing for user {state['user_id']}")
    user_id = state["user_id"]

    messages = state.get("messages", [])
    last_human = next(
        (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
    )
    if not last_human:
        return {**state, "tool_results": [], "selected_agent": "order_agent"}

    tool_results = []

    # If no API key, call tools directly using rule-based approach
    if not settings.OPENROUTER_API_KEY:
        order_context = state.get("order_context") or {}
        order_number = order_context.get("order_number")

        if order_number:
            result = ORDER_TOOLS[0].invoke({"order_number": order_number, "user_id": user_id})
            tool_results.append({
                "tool": "get_order_status",
                "input": {"order_number": order_number},
                "output": result,
            })
        else:
            result = ORDER_TOOLS[1].invoke({"user_id": user_id})
            tool_results.append({
                "tool": "list_recent_orders",
                "input": {},
                "output": result,
            })

        return {**state, "tool_results": tool_results, "selected_agent": "order_agent"}

    try:
        llm_with_tools = _get_llm_with_tools()

        # Include order number in the user message context if available
        order_context = state.get("order_context") or {}
        context_note = ""
        if order_context.get("order_number"):
            context_note = f"\n[Order Number from context: {order_context['order_number']}]"

        agent_messages = [
            SystemMessage(content=ORDER_AGENT_PROMPT),
            HumanMessage(content=f"{last_human.content}{context_note}\n\n[user_id: {user_id}]"),
        ]

        response = llm_with_tools.invoke(agent_messages)

        # Execute tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            tool_map = {t.name: t for t in ORDER_TOOLS}
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("args", {})
                # Inject user_id if needed
                if "user_id" in tool_map.get(tool_name, {tool_name: None}.__class__.__mro__):
                    tool_args.setdefault("user_id", user_id)

                tool_func = tool_map.get(tool_name)
                if tool_func:
                    # Ensure user_id is passed
                    if "user_id" not in tool_args:
                        tool_args["user_id"] = user_id
                    output = tool_func.invoke(tool_args)
                    tool_results.append({
                        "tool": tool_name,
                        "input": tool_args,
                        "output": output,
                    })

        if not tool_results:
            # Fallback: call list_recent_orders
            output = ORDER_TOOLS[1].invoke({"user_id": user_id})
            tool_results.append({
                "tool": "list_recent_orders",
                "input": {},
                "output": output,
            })

    except Exception as e:
        logger.error(f"Order agent failed: {e}", exc_info=True)
        # Graceful fallback
        output = ORDER_TOOLS[1].invoke({"user_id": user_id})
        tool_results.append({
            "tool": "list_recent_orders",
            "input": {},
            "output": output,
        })

    return {**state, "tool_results": tool_results, "selected_agent": "order_agent"}
