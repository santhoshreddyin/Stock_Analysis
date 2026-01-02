import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent
import inspect
from rich import print

def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val

def _get_chat_model():
    """
    Prefer local Ollama by default to avoid implicit Anthropic usage.
    If you want Anthropic/OpenAI, set ANTHROPIC_API_KEY / OPENAI_API_KEY.
    """
    if os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-5"), temperature=0.2)

    from langchain_ollama import ChatOllama  # type: ignore
    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "kimi-k2:1t-cloud"),
        temperature=0.2,
        timeout=120,
    )

tavily_client = TavilyClient(api_key=_require_env("TAVILY_API_KEY"))

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# System prompt to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
"""

def _create_agent():
    kwargs = dict(
        tools=[internet_search],
        system_prompt=research_instructions,
    )
    sig = inspect.signature(create_deep_agent)
    if "model" in sig.parameters:
        kwargs["model"] = _get_chat_model()
    elif "llm" in sig.parameters:
        kwargs["llm"] = _get_chat_model()
    return create_deep_agent(**kwargs)

if __name__ == "__main__":
    agent = _create_agent()
    result = agent.invoke({"messages": [{"role": "user", "content": "What is the Latest developments in the Field of AI in 2025?"}]})
    print(result)
    # Print the agent's response
    print(result["messages"][-1].content)