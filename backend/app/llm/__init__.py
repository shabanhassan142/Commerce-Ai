"""
llm/ — LLM Provider Interface (Module 4)

Provides a configurable, provider-agnostic LLM interface:
  - LLMProvider: Abstract base class
  - OpenRouterProvider: Default provider (OpenRouter API)
  - get_llm_provider(): Factory function (reads from settings)
  - Supported models: qwen/qwen3-30b-a3b:free (default)

Design:
  The provider is configured via environment variables,
  allowing future swap to Anthropic, OpenAI, or local models
  without changing agent code.

  settings.LLM_PROVIDER = "openrouter" | "openai" | "anthropic"
  settings.LLM_MODEL    = "qwen/qwen3-30b-a3b:free"

Implemented in Module 4.
"""
