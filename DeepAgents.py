import os
import sys
import argparse
import asyncio
from rich import print
from typing import Literal
from HelperFunctions import _require_env

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from deepagents import create_deep_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langfuse.langchain import CallbackHandler
from deepagents.backends import FilesystemBackend

langfuse_handler = CallbackHandler()
import httpx
import anyio

# Helper Functions
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
            return await agent.ainvoke(payload,config={"callbacks":[langfuse_handler]})
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


# MCP Tool: Send Email via Gmail SMTP
import smtplib
from email.message import EmailMessage

def send_gmail_email(
    subject: str,
    body: str,
) -> str:
    """
    Send an email via Gmail SMTP (synchronous).

    Env vars:
      - GMAIL_SMTP_USER: your Gmail address (or Google Workspace user)
      - GMAIL_APP_PASSWORD: 16-char Gmail App Password (recommended)
    """
    smtp_user = _require_env("GMAIL_SMTP_USER")
    app_password = _require_env("GMAIL_APP_PASSWORD")

    msg = EmailMessage()
    msg["From"] = smtp_user
    msg["To"] = "santhoshreddyin@gmail.com"  # For simplicity, sending to self only
    msg["Subject"] = subject
    msg.set_content(body, subtype="html")

    # Gmail SMTP over SSL (sync)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(smtp_user, app_password)
        smtp.send_message(msg, from_addr=smtp_user, to_addrs="santhoshreddyin@gmail.com")

    return f"email sent"

def read_report_file(file_path: str) -> str:
    """Read the content of a report file (also searches nested ./AgentMemory)."""
    project_root = os.path.dirname(os.path.abspath(__file__))
    agent_memory_root = os.path.join(project_root, "AgentMemory")

    def _try_read(path: str) -> str | None:
        if os.path.exists(path) and os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        return None

    # 1) Exact path as provided
    content = _try_read(file_path)
    if content is not None:
        return content

    # 2) Relative to project root
    if not os.path.isabs(file_path):
        content = _try_read(os.path.join(project_root, file_path))
        if content is not None:
            return content

        # 3) Relative to AgentMemory root
        content = _try_read(os.path.join(agent_memory_root, file_path))
        if content is not None:
            return content

    # 4) Recursive search inside AgentMemory (nested)
    target_name = os.path.basename(file_path)
    matches: list[str] = []
    if os.path.isdir(agent_memory_root) and target_name:
        for root, _, files in os.walk(agent_memory_root):
            if target_name in files:
                matches.append(os.path.join(root, target_name))

    if matches:
        best = max(matches, key=lambda p: os.path.getmtime(p))
        content = _try_read(best)
        if content is not None:
            return content

    return "Report file does not exist."

_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
_YFINANCE_MCP_PATH = os.path.join(_PROJECT_ROOT, "MCP_Servers", "yfinance_MCP.py")
_PLAYWRIGHT_MCP_PATH = os.path.join(_PROJECT_ROOT, "MCP_Servers", "playwright_MCP.py")

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
        "playwright_MCP": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [_PLAYWRIGHT_MCP_PATH],
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

async def _open_playwright_session():
    if not os.path.exists(_PLAYWRIGHT_MCP_PATH):
        raise FileNotFoundError(f"Playwright MCP not found at: {_PLAYWRIGHT_MCP_PATH}")
    try:
        return client.session("playwright_MCP")
    except anyio.BrokenResourceError as e:
        raise RuntimeError(
            "MCP stdio channel broke. The Playwright MCP server likely crashed.\n"
            f"Try running it directly to see the real error:\n  {sys.executable} {_PLAYWRIGHT_MCP_PATH}"
        ) from e

# Model Initialization
async def main(args: argparse.Namespace) -> None:
    api_key = _require_env("OPENAI_API_KEY")

    model = ChatOpenAI(
        model="gpt-5-nano", #os.getenv("OPENAI_MODEL", "gpt-5"),
        temperature=0.1,
        max_tokens=_int_env("OPENAI_MAX_TOKENS", 6000),   # was 50000
        timeout=_float_env("OPENAI_TIMEOUT", 600.0),      # was 120
        max_retries=_int_env("OPENAI_MAX_RETRIES", 2),
        api_key=api_key,
    )
    
    try:
        async with (await _open_yfinance_session()) as yfinance_session, \
                   (await _open_playwright_session()) as playwright_session:
            yfinance_tools = await load_mcp_tools(yfinance_session)
            playwright_tools = await load_mcp_tools(playwright_session)

            subagents = [
            {
                "name": "Technical_Analyst",
                "model": model,
                "description": "Provides the Technical Analysis of stocks",
                "system_prompt": "Analyze data and extract key insights such as Support and Resistance levels, Moving Averages, Share holding Patterns, PE Ratios, Insider trading and other technical indicators.",
                "tools": yfinance_tools,
            },
            {
                "model": model,
                "name": "Fundamental_Analyst",
                "description": "Provides the Fundamental Analysis of stocks",
                "system_prompt": "Analyze the Stock from the fundamental perspective. Look at the Industry Trends, MOAT, Competitors, Financial Health, Management Effectiveness and other fundamental indicators.",
                "tools": yfinance_tools,
            },
            {
                "model": model,
                "name": "News_Analyst",
                "description": "Gathers latest news and updates on stocks using web scraping and search",
                "system_prompt": """Analyze the Recent Stock News and summarize the important events impacting the stock price.
                
                You have access to:
                - internet_search: For general web search and finding news sources
                - Playwright tools for deep web scraping:
                  * scrape_news_article: Extract full article content from news URLs
                  * scrape_page_content: Scrape content from any web page
                  * navigate_to_url: Navigate to a URL and get basic info
                  * extract_links: Extract all links from a page
                  * take_screenshot: Capture screenshots of web pages
                
                Use internet_search to find relevant news sources, then use scrape_news_article or scrape_page_content to extract detailed information from those sources.""",
                "tools": [internet_search] + playwright_tools,
            },
            {
                "model": model,
                "name": "User_Notifier",
                "description": "Writes polished outputs and communicates results to the user",
                "backend": FilesystemBackend(root_dir="./AgentMemory/Output", virtual_mode=True),
                "system_prompt": """
                Goal:
                Send beautified professional html report to the End user via email.
                
                Guidelines:
                1. Read the Report using read_report_file tool. 
                2. Use HTML formatting to enhance the visual appeal of the email.
                3. Include relevant charts, graphs, or images to support your analysis.
                4. Use appropriate headings, subheadings, and bullet points to organize the content.
                5. Ensure that the email is mobile-friendly and displays correctly on various devices.
                6. Proofread the email for grammar, spelling, and clarity before sending.
                7. The email should have a clear and concise subject line summarizing the content.
                8. Ensure the tone of the email is professional and courteous.
                9. No Mentions of internal processes, subagents, or analysis methods, followup questions etc.
                10. Sign off the email with a polite closing statement.                
                """,
                "tools": [send_gmail_email,read_report_file],
            },
            ]

            research_instructions = """
            Goals:
            1. You are an Stock Analyst. 
            2. Your job is to Analyse stocks and provide detailed insights.
            
            Guidelines:
            1. You must perform the following types of analysis using your subagents:
                a. Fundamental Analysis
                b. Technical Analysis
                c. News Analysis
                d. Any other analysis you deem fit. If you need additional information, use the internet search tool to gather more data.
            2. Be Mindful of the token cost while interacting with the subagents. Don't call them more than necessary. E.g.if you have already gathered fundamental data or Technical Data very recently,avoid calling the relevant subagent again. 
            3. After gathering insights from all subagents, you must compile a comprehensive report summarizing your findings
            4. You must write the key observayions in {STOCK_SYMBOL}_Analysis.txt file in the AgentMemory directory so as to no repeat the full research next time.
            5. If the file does not exist, perform full analysis to create it.
            6. If the file exists, read it and perform only incremental analysis to update it. Updates should be appended to the file and clearly marked with date and time.
            7. When sending the report, Refer to the file and provide the incremental insights only.
            8. Do not ask for any additional information from the user. Take full responsibility for the analysis and report generation.
            9. You must use the User_Notifier subagent to write the final report.
            10.Optionally use Self_Notes.txt file in the AgentMemory directory to Only to keep track of your observations on the analysis process and sub Agents Behaviours for improving future analyses.
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
        default="Analyse SMCI stock",
        help="User prompt to send to the agent",
    )
    asyncio.run(main(parser.parse_args()))
