"""
graph/ — LangGraph State Graph (Module 4)

Defines the CommerceFlow AI conversation graph:
  - ConversationState: Typed state passed between nodes
  - build_graph(): Compiles the LangGraph StateGraph
  - Nodes: supervisor, order_agent, refund_agent, billing_agent,
           product_agent, knowledge_agent, support_agent,
           escalation_agent, response_agent

Flow:
  START → Supervisor → Intent Classification → Agent Selection
        → Retrieve Data → Generate Response → Confidence Check
        → Respond (high confidence) or Escalate (low confidence) → END

Implemented in Module 4.
"""
