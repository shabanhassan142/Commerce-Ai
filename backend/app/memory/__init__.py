"""
memory/ — Conversation & Customer Memory (Module 4)

Manages short-term and long-term memory for the AI agents:
  - ConversationMemory: Stores messages within a session
  - CustomerMemory: Persists customer preferences and history
  - MemoryStore: Database-backed persistence layer

Memory types:
  - Conversation Memory: Recent messages in the active session
  - Customer Memory: Customer profile, order history, past tickets
  - Order History: Previous orders and their statuses
  - Recent Messages: Last N messages for context window

Implemented in Module 4.
"""
