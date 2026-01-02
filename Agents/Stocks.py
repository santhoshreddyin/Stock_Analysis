import asyncio
import os
import argparse
import getpass
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from rich import print
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
import sys


client = MultiServerMCPClient(  
    {
        "yfinance_MCP": {
            "transport": "stdio",  # Local subprocess communication
            "command": "python",
            "command": sys.executable,
            "args": ["./MCP_Servers/yfinance_MCP.py"],
        },
    }
)

async def main(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")

    model = ChatOpenAI(
        model="gpt-5-mini",
        temperature=0.1,
        max_tokens=50000,
        timeout=120,
        api_key=api_key,
    )

    async with client.session("yfinance_MCP") as session:  
        # Pass the session to load tools, resources, or prompts
        tools = await load_mcp_tools(session)  
        agent = create_agent(
            model=model,
            tools=tools,
            system_prompt="You are a helpful assistant",
        )

        # Run the agent
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": args.prompt}]}
        )

        print(result)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", dest="api_key", default=None, help="OpenAI API key (overrides OPENAI_API_KEY env var)")
    parser.add_argument(
        "--prompt",
        default="Analyse the latest news on IONQ",
        help="User prompt to send to the agent",
    )
    asyncio.run(main(parser.parse_args()))
