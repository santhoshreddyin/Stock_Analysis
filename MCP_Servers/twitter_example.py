#!/usr/bin/env python3
"""
Example script demonstrating Twitter MCP server usage.

This script shows how to use the Twitter tools for stock analysis.
Make sure TWITTER_BEARER_TOKEN is set in your environment before running.

Usage:
    python twitter_example.py
"""

import os
import sys
import asyncio
from rich import print

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools


async def main():
    """Demonstrate Twitter MCP tools."""
    
    # Check for Twitter bearer token
    if not os.getenv("TWITTER_BEARER_TOKEN"):
        print("[red]Error: TWITTER_BEARER_TOKEN environment variable not set[/red]")
        print("Please set it with: export TWITTER_BEARER_TOKEN='your_token_here'")
        sys.exit(1)
    
    print("[green]✓ Twitter Bearer Token found[/green]")
    print()
    
    # Set up MCP client
    twitter_mcp_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "twitter_MCP.py"
    )
    
    client = MultiServerMCPClient({
        "twitter_MCP": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [twitter_mcp_path],
            "env": dict(os.environ),
        }
    })
    
    print("[cyan]Connecting to Twitter MCP server...[/cyan]")
    
    try:
        async with client.session("twitter_MCP") as session:
            # Load available tools
            tools = await load_mcp_tools(session)
            print(f"[green]✓ Loaded {len(tools)} Twitter tools[/green]")
            print()
            
            # Display available tools
            print("[bold]Available Tools:[/bold]")
            for tool in tools:
                print(f"  - {tool.name}: {tool.description}")
            print()
            
            # Example 1: Search for tweets about a stock
            print("[bold cyan]Example 1: Search for tweets about NVDA stock[/bold cyan]")
            print("-" * 60)
            
            search_tool = next((t for t in tools if t.name == "search_tweets"), None)
            if search_tool:
                result = await search_tool.ainvoke({
                    "query": "$NVDA OR nvidia stock",
                    "max_results": 3,
                    "only_genuine": True,
                    "min_followers": 5000
                })
                
                if result:
                    print(f"[green]Found {len(result)} tweets:[/green]")
                    for i, tweet in enumerate(result, 1):
                        print(f"\n[yellow]Tweet {i}:[/yellow]")
                        print(f"  Author: @{tweet['author']['username']} ({tweet['author']['name']})")
                        print(f"  Verified: {'✓' if tweet['author']['verified'] else '✗'}")
                        print(f"  Followers: {tweet['author']['followers_count']:,}")
                        print(f"  Text: {tweet['text'][:200]}{'...' if len(tweet['text']) > 200 else ''}")
                        print(f"  Likes: {tweet['metrics']['like_count']}, Retweets: {tweet['metrics']['retweet_count']}")
                        print(f"  URL: {tweet['url']}")
                else:
                    print("[yellow]No tweets found[/yellow]")
            print()
            
            # Example 2: Get user information
            print("[bold cyan]Example 2: Check user credibility[/bold cyan]")
            print("-" * 60)
            
            user_tool = next((t for t in tools if t.name == "get_user_info"), None)
            if user_tool:
                # Example with a known financial account (replace with actual username)
                test_users = ["elonmusk", "jimcramer", "zerohedge"]
                
                for username in test_users:
                    try:
                        user_info = await user_tool.ainvoke({"username": username})
                        
                        if "error" not in user_info:
                            print(f"\n[yellow]User: @{username}[/yellow]")
                            print(f"  Name: {user_info['name']}")
                            print(f"  Verified: {'✓' if user_info['verified'] else '✗'}")
                            print(f"  Followers: {user_info['public_metrics']['followers_count']:,}")
                            print(f"  Following: {user_info['public_metrics']['following_count']:,}")
                            print(f"  Tweets: {user_info['public_metrics']['tweet_count']:,}")
                            print(f"  Genuine: {'✓' if user_info['genuinity']['is_genuine'] else '✗'}")
                            print(f"  Reason: {user_info['genuinity']['reason']}")
                        else:
                            print(f"[red]Could not find user @{username}[/red]")
                    except Exception as e:
                        print(f"[red]Error checking @{username}: {str(e)}[/red]")
                        break
            print()
            
            # Example 3: Get tweets from a specific user
            print("[bold cyan]Example 3: Get tweets from a financial analyst[/bold cyan]")
            print("-" * 60)
            
            user_tweets_tool = next((t for t in tools if t.name == "search_tweets_by_user"), None)
            if user_tweets_tool:
                # Try a known financial account
                try:
                    result = await user_tweets_tool.ainvoke({
                        "username": "zerohedge",  # Financial news account
                        "max_results": 3,
                        "exclude_replies": True,
                        "exclude_retweets": True
                    })
                    
                    if result:
                        print(f"[green]Found {len(result)} recent tweets:[/green]")
                        for i, tweet in enumerate(result, 1):
                            print(f"\n[yellow]Tweet {i}:[/yellow]")
                            print(f"  Date: {tweet['created_at']}")
                            print(f"  Text: {tweet['text'][:200]}{'...' if len(tweet['text']) > 200 else ''}")
                            print(f"  Engagement: {tweet['metrics']['like_count']} likes, {tweet['metrics']['retweet_count']} RTs")
                    else:
                        print("[yellow]No tweets found[/yellow]")
                except Exception as e:
                    print(f"[red]Error: {str(e)}[/red]")
            
            print()
            print("[green]✓ Demo completed successfully![/green]")
            
    except Exception as e:
        print(f"[red]Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    print("[bold]Twitter/X MCP Server Demo[/bold]")
    print("=" * 60)
    print()
    
    asyncio.run(main())
