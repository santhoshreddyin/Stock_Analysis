import asyncio
import argparse
from langchain.agents import create_agent
from rich import print
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
import sys
from langchain_ollama import ChatOllama
import os
import subprocess
import json


# Try loading .env if available (optional dependency).
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

_CLIENT_CONFIG = {
    "yfinance_MCP": {
        "transport": "stdio",
        "command": sys.executable,
        "args": ["./MCP_Servers/yfinance_MCP.py"],
    },
}

def _get_client() -> MultiServerMCPClient:
    """
    Streamlit reruns the script frequently; cache the client when possible.
    Falls back to a fresh client when Streamlit isn't available.
    """
    try:
        import streamlit as st  # type: ignore

        @st.cache_resource
        def _cached_client() -> MultiServerMCPClient:
            return MultiServerMCPClient(_CLIENT_CONFIG)

        return _cached_client()
    except Exception:
        return MultiServerMCPClient(_CLIENT_CONFIG)

async def run_agent(prompt: str):
    model = ChatOllama(
        model="kimi-k2:1t-cloud",
        temperature=0.1,
        max_tokens=50000,
        timeout=120,
    )

    client = _get_client()
    async with client.session("yfinance_MCP") as session:
        tools = await load_mcp_tools(session)
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt="You are a helpful assistant",
        )

        return await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

def _running_in_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx  # type: ignore
        return get_script_run_ctx() is not None
    except Exception:
        return False

def _coerce_to_text(res) -> str:
    if res is None:
        return ""
    if isinstance(res, str):
        return res.strip()

    # Common LangChain patterns:
    if isinstance(res, dict):
        if "output" in res and isinstance(res["output"], str):
            return res["output"].strip()

        msgs = res.get("messages")
        if isinstance(msgs, list) and msgs:
            last = msgs[-1]
            if isinstance(last, dict) and isinstance(last.get("content"), str):
                return last["content"].strip()
            content = getattr(last, "content", None)
            if isinstance(content, str):
                return content.strip()

        return json.dumps(res, indent=2, default=str)

    content = getattr(res, "content", None)
    if isinstance(content, str):
        return content.strip()

    return str(res).strip()

def streamlit_app() -> None:
    import streamlit as st  # type: ignore

    st.set_page_config(page_title="AI Trading Agent (yfinance MCP)", layout="wide")
    st.title("AI Trading Agent (yfinance MCP)")

    default_prompt = (
        "Analyse the NVDA,AAPL,GOOG,MSFT,AMZN,META,TSLA stock performance over the last week. "
        "Find the reasons for the behaviour and future prospects, key milestones."
    )

    prompt = st.text_area("Prompt", value=default_prompt, height=140)

    col1, col2 = st.columns([1, 5])
    run_clicked = col1.button("Run", type="primary")
    status_ph = col2.empty()

    out = st.session_state.get("output", "")
    out_ph = st.empty()

    if run_clicked:
        if not prompt.strip():
            st.session_state["output_md"] = "Please enter a prompt."
            st.session_state["output_raw"] = ""
            return

        status_ph.info("Running...")
        with st.spinner("Running agent..."):
            try:
                res = asyncio.run(run_agent(prompt.strip()))
                st.session_state["output_raw"] = res
                st.session_state["output_md"] = _coerce_to_text(res) or "(No output)"
                status_ph.success("Done")
            except Exception as e:
                st.session_state["output_raw"] = ""
                st.session_state["output_md"] = f"**Error:** `{type(e).__name__}`\n\n{e}"
                status_ph.error("Error")

    st.subheader("Output")
    st.markdown(st.session_state.get("output_md", ""))

    with st.expander("Raw response (debug)", expanded=False):
        st.code(
            json.dumps(st.session_state.get("output_raw", ""), indent=2, default=str)
            if not isinstance(st.session_state.get("output_raw", ""), str)
            else st.session_state.get("output_raw", ""),
            language="json",
        )

def _launch_streamlit() -> int:
    script_path = os.path.abspath(__file__)
    cmd = [sys.executable, "-m", "streamlit", "run", script_path]
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        print("Streamlit is not installed. Install with:\n  pip install streamlit")
        return 1

if __name__ == "__main__":
    if _running_in_streamlit():
        streamlit_app()
        raise SystemExit(0)

    parser = argparse.ArgumentParser()
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit UI")
    parser.add_argument("--api-key", dest="api_key", default=None, help="OpenAI API key (unused for Ollama)")
    parser.add_argument(
        "--prompt",
        default="Analyse the NVDA,AAPL,GOOG,MSFT,AMZN,META,TSLA stock performance of over the last week. Find the reasons for the behaviour and future prospects, Key milestones.",
        help="User prompt to send to the agent",
    )
    args = parser.parse_args()

    if args.ui:
        raise SystemExit(_launch_streamlit())
    else:
        print(asyncio.run(run_agent(args.prompt)))