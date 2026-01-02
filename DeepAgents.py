import os
import sys
import argparse
import asyncio
from rich import print
from typing import Literal

from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

import httpx
import anyio

# Helper Functions
def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except Exception:
        return default

def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "").strip() or default)
    except Exception:
        return default

def _is_retryable(e: Exception) -> bool:
    if isinstance(e, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    return type(e).__name__ in {
        "APITimeoutError",
        "APIConnectionError",
        "RateLimitError",
        "InternalServerError",
        "ServiceUnavailableError",
    }

async def _ainvoke_with_retries(agent, payload: dict):
    attempts = _int_env("AGENT_RETRIES", 3)
    base_delay = _float_env("AGENT_RETRY_BASE_DELAY", 1.5)

    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return await agent.ainvoke(payload)
        except Exception as e:
            last = e
            if i >= attempts or not _is_retryable(e):
                raise
            delay = base_delay * (2 ** (i - 1))
            print(f"[yellow]Transient error ({type(e).__name__}). Retrying in {delay:.1f}s... ({i}/{attempts})[/yellow]")
            await asyncio.sleep(delay)

    raise last  # type: ignore[misc]

# Tool/MCP Definitions
from tavily import TavilyClient
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

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_YFINANCE_MCP_PATH = os.path.join(_PROJECT_ROOT, "MCP_Servers", "yfinance_MCP.py")

def _mcp_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env

client = MultiServerMCPClient(
    {
        "yfinance_MCP": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [_YFINANCE_MCP_PATH],
            "env": _mcp_env(),
        },
    }
)

async def _open_yfinance_session():
    if not os.path.exists(_YFINANCE_MCP_PATH):
        raise FileNotFoundError(f"yfinance MCP not found at: {_YFINANCE_MCP_PATH}")
    try:
        return client.session("yfinance_MCP")
    except anyio.BrokenResourceError as e:
        raise RuntimeError(
            "MCP stdio channel broke. The yfinance MCP server likely crashed.\n"
            f"Try running it directly to see the real error:\n  {sys.executable} {_YFINANCE_MCP_PATH}"
        ) from e

# Model Initialization
async def main(args: argparse.Namespace) -> None:
    api_key = _require_env("OPENAI_API_KEY")

    model = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-5"),
        temperature=0.1,
        max_tokens=_int_env("OPENAI_MAX_TOKENS", 6000),   # was 50000
        timeout=_float_env("OPENAI_TIMEOUT", 600.0),      # was 120
        max_retries=_int_env("OPENAI_MAX_RETRIES", 2),
        api_key=api_key,
    )

    try:
        async with (await _open_yfinance_session()) as session:
            tools = await load_mcp_tools(session)

            subagents = [
            {
                "name": "Technical_Analyst",
                "description": "Provides the Technical Analysis of stocks",
                "system_prompt": "Analyze data and extract key insights such as Support and Resistance levels, Moving Averages, Share holding Patterns, PE Ratios, Insider trading and other technical indicators.",
                "tools": tools,
            },
            {
                "name": "Fundamental_Analyst",
                "description": "Provides the Fundamental Analysis of stocks",
                "system_prompt": "Analyze data and extract key insights",
            },
            {
                "name": "News_Reporter",
                "description": "Gathers latest news and updates on stocks",
                "system_prompt": "Create professional reports from insights",
                "tools": [internet_search],
            },
            {
                "name": "User_Notifier",
                "description": "Writes polished reports from analysis",
                "system_prompt": "Create professional reports from insights",
            },
            ]

            from deepagents.backends import FilesystemBackend
            research_instructions = """You are an expert researcher. Your job is to conduct thorough research, and then write a polished report.
    Keep the final answer concise and well-structured unless the user asks for exhaustive detail.
    """

            agent = create_deep_agent(
                model=model,
                system_prompt=research_instructions,
                backend=FilesystemBackend(root_dir="./AgentMemory/", virtual_mode=True),
                subagents=subagents,
            )

            result = await _ainvoke_with_retries(
                agent,
                {"messages": [{"role": "user", "content": args.prompt}]},
            )

            print(result)
            print(result["messages"][-1].content)
    except anyio.BrokenResourceError as e:
        raise RuntimeError(
            "MCP stdio channel broke mid-run. The yfinance MCP server likely exited unexpectedly.\n"
            f"Run it directly to debug:\n  {sys.executable} {_YFINANCE_MCP_PATH}"
        ) from e

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    #parser.add_argument("--api-key", dest="api_key", default=None, help="OpenAI API key (overrides OPENAI_API_KEY env var)")
    parser.add_argument(
        "--prompt",
        default="Analyse IONQ stock",
        help="User prompt to send to the agent",
    )
    asyncio.run(main(parser.parse_args()))
