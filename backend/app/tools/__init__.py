"""
tools/ — Agent Tool Definitions (Module 5)

LangGraph-compatible tools available to all agents:
  - search_orders(customer_id, order_id): Query order data
  - search_customers(email, customer_id): Query customer data
  - search_products(query, category): Query product catalog
  - search_policies(query): Semantic search in FAISS
  - search_faq(query): Semantic search for FAQs
  - search_tickets(customer_id): Query support tickets
  - create_ticket(customer_id, subject, description): Open ticket
  - update_ticket(ticket_id, status, notes): Update ticket
  - store_conversation(session_id, messages): Persist conversation
  - retrieve_history(customer_id): Get conversation history
  - generate_summary(messages): Summarize conversation

Implemented in Module 5.
"""
