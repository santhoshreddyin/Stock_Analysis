import asyncio
import os
import argparse
import getpass
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from rich import print
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# Try loading .env if available (optional dependency).
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

client = MultiServerMCPClient(  
    {
        "yfinance": {
            "transport": "stdio",  # Local subprocess communication
            "command": "python",
            # Absolute path to your math_server.py file
            "args": ["./MCP_Servers/yfinance.py"],
        },
    }
)

async def main(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")

    model = ChatOpenAI(
        model="gpt-5-mini",
        temperature=0.1,
        max_tokens=1000,
        timeout=30,
        api_key=api_key,
    )

    async with client.session("yfinance") as session:  
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
        default="Analyse the stock performance of AAPL over the last month and provide insights.",
        help="User prompt to send to the agent",
    )
    asyncio.run(main(parser.parse_args()))
