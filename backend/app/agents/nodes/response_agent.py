"""
app/agents/nodes/response_agent.py

Response Agent node — synthesizes the final answer from tool results.
Also computes confidence score and decides if escalation is needed.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agents.state import CommerceFlowState
from app.config.settings import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

RESPONSE_PROMPT = """You are CommerceFlow AI, a friendly and knowledgeable e-commerce assistant.

Your job: Synthesize tool results into a natural, conversational response for the customer.

== STRICT RULES ==

1. NEVER output raw tool internals. The following are FORBIDDEN in your response:
   - "Found N products matching '...':"
   - "Tool result:", "Agent result:", "SEARCH RESULTS"
   - Any mention of "product_agent", "search_products", "tool", "agent"
   - Internal SKU searches or debug information

2. ATTRIBUTE NOT AVAILABLE → Be honest. If the tool result says "I don't have [X] information"
   or "Not available in catalog", convey this honestly:
   ✅ "I don't have country-of-origin information for [Product] in our catalog."
   ✅ "Warranty details aren't listed for this product yet."
   ❌ NEVER invent specifications, warranty, or origin information.

3. GREETING / GENERAL CONVERSATION → Respond warmly and naturally. Do NOT mention products
   or search results unless the user asked about them.

4. PRODUCT INFORMATION → Present the product clearly with name, price, rating, availability.
   Use **bold** for product name. Use bullet points for specs.

5. PRICE QUERY → State the price clearly in PKR. Mention discount if applicable.

6. STOCK QUERY → State clearly whether in stock and quantity if available.

7. COMPARISON → Format as a markdown table if the tool returned comparison data.
   Include only attributes actually present in the data — never add imagined rows.

8. CLARIFICATION NEEDED → If the tool said "Which product are you asking about?",
   ask the user naturally: "Which product are you referring to? Could you share the product name?"

9. SEARCH RESULTS → When presenting multiple products, list them naturally (numbered) with
   price and rating. Do NOT say "Found N products matching '...'". Instead say something like
   "Here are some [category] options I found for you:"

10. NO HALLUCINATION → If data is missing, say so. Never invent product details.

11. Keep responses concise (under 300 words) unless a comparison table requires more.

Context:
  Intent: {intent}
  Active Product: {active_product}
"""

CONFIDENCE_THRESHOLDS = {
    "tool_success": 0.7,       # tool ran without error
    "tool_error": 0.3,         # tool returned an error
    "rag_high_score": 0.75,    # RAG found relevant docs with score > 0.6
    "rag_low_score": 0.5,      # RAG found docs but low relevance
    "rag_no_results": 0.35,    # no RAG results
    "no_tools": 0.4,           # agent ran but no tools were called
    "general": 0.6,            # general/greeting intent
}


def _compute_confidence(state: CommerceFlowState) -> float:
    """Compute confidence score based on tool results and RAG scores."""
    intent = state.get("intent", "general")
    tool_results = state.get("tool_results", [])
    retrieved_docs = state.get("retrieved_documents", [])

    if intent == "general":
        return CONFIDENCE_THRESHOLDS["general"]

    if not tool_results:
        return CONFIDENCE_THRESHOLDS["no_tools"]

    # Check if any tool returned an error
    has_error = any(
        "error" in str(r.get("output", "")).lower()
        for r in tool_results
    )

    if intent == "knowledge":
        if not retrieved_docs:
            return CONFIDENCE_THRESHOLDS["rag_no_results"]
        max_score = max((r.get("score", 0) for r in retrieved_docs), default=0)
        if max_score >= 0.6:
            return CONFIDENCE_THRESHOLDS["rag_high_score"]
        return CONFIDENCE_THRESHOLDS["rag_low_score"]

    return CONFIDENCE_THRESHOLDS["tool_error"] if has_error else CONFIDENCE_THRESHOLDS["tool_success"]


def _format_tool_context(state: CommerceFlowState) -> str:
    """Format tool results into a context string for the LLM."""
    tool_results = state.get("tool_results", [])
    retrieved_docs = state.get("retrieved_documents", [])
    citations = state.get("citations", [])

    lines = []

    if tool_results:
        lines.append("=== Tool Results ===")
        for r in tool_results:
            lines.append(f"[{r.get('tool', 'tool')}]:")
            lines.append(str(r.get("output", "")))
            lines.append("")

    if retrieved_docs and citations:
        lines.append("=== Knowledge Base Sources ===")
        for c in citations:
            lines.append(f"[Source {c['index']}: {c['source']} (relevance: {c['score']})]")
            lines.append(c.get("text_preview", ""))
            lines.append("")

    return "\n".join(lines) if lines else "No tool results available."


def _fallback_response(state: CommerceFlowState) -> str:
    """Generate response from tool results without LLM."""
    tool_results = state.get("tool_results", [])
    intent = state.get("intent", "general")

    if not tool_results:
        return (
            "Hello! I'm CommerceFlow AI's virtual assistant. "
            "How can I help you today? I can assist with:\n"
            "  - Order status and tracking\n"
            "  - Product search and information\n"
            "  - Returns and refunds\n"
            "  - Shipping and payment questions"
        )

    # Use the tool output directly
    outputs = [str(r.get("output", "")) for r in tool_results]
    combined = "\n\n".join(outputs)

    # Add a friendly wrapper
    if intent == "order":
        return f"Here's the information about your order:\n\n{combined}\n\nIs there anything else I can help you with?"
    elif intent == "product":
        return f"{combined}\n\nWould you like more details on any of these products?"
    elif intent == "refund":
        return f"{combined}\n\nIf you need further assistance with your return, feel free to ask!"
    elif intent == "knowledge":
        return f"Based on our policies:\n\n{combined}\n\nIs there anything else I can clarify?"
    else:
        return f"{combined}\n\nIs there anything else I can help you with?"


def response_agent_node(state: CommerceFlowState) -> CommerceFlowState:
    """
    Response Agent: synthesize final answer and compute confidence.
    """
    logger.info(f"Response agent synthesizing for conversation {state['conversation_id']}")

    # Compute confidence
    confidence = _compute_confidence(state)
    requires_escalation = confidence < 0.4

    if not settings.OPENROUTER_API_KEY:
        # Fallback: use tool results directly
        response = _fallback_response(state)
        ai_message = AIMessage(content=response)
        return {
            **state,
            "response": response,
            "confidence": confidence,
            "requires_escalation": requires_escalation,
            "messages": state.get("messages", []) + [ai_message],
        }

    try:
        tool_context = _format_tool_context(state)
        messages = state.get("messages", [])
        last_human = next(
            (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
        )

        active_product = state.get("active_product")
        active_product_name = active_product.get("name", "None") if active_product else "None"
        system_prompt = RESPONSE_PROMPT.format(
            intent=state.get("resolved_intent", state.get("intent", "general")),
            active_product=active_product_name,
        )

        api_key = settings.OPENROUTER_API_KEY
        llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            openai_api_key=api_key,
            openai_api_base=settings.OPENROUTER_BASE_URL,
            default_headers={"HTTP-Referer": "https://commerceflow.ai", "X-Title": "CommerceFlow AI"},
        )

        prompt_messages = [SystemMessage(content=system_prompt)]
        # Add conversation history (last 4 turns)
        recent_messages = [m for m in messages[-8:] if not isinstance(m, AIMessage) or m != messages[-1]]
        prompt_messages.extend(recent_messages)
        prompt_messages.append(
            HumanMessage(
                content=f"Tool Results:\n{tool_context}\n\nGenerate the final customer response."
            )
        )

        response_msg = llm.invoke(prompt_messages)
        response = response_msg.content.strip()

        ai_message = AIMessage(content=response)
        return {
            **state,
            "response": response,
            "confidence": confidence,
            "requires_escalation": requires_escalation and state.get("intent") not in ["general"],
            "messages": state.get("messages", []) + [ai_message],
        }

    except Exception as e:
        logger.error(f"Response agent LLM failed: {e}", exc_info=True)
        response = _fallback_response(state)
        ai_message = AIMessage(content=response)
        return {
            **state,
            "response": response,
            "confidence": max(confidence - 0.1, 0.2),
            "requires_escalation": confidence < 0.4,
            "messages": state.get("messages", []) + [ai_message],
        }


def route_after_response(state: CommerceFlowState) -> str:
    """Route to escalation if needed, otherwise end."""
    if state.get("requires_escalation") and not state.get("ticket_id"):
        return "escalation_node"
    return "__end__"
