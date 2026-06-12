"""LLM providers: a minimal protocol, the OpenAI adapter, and a scriptable fake."""

from text_to_sql_engine.llm.base import LLMProvider
from text_to_sql_engine.llm.fake import FakeLLM

__all__ = ["FakeLLM", "LLMProvider"]
