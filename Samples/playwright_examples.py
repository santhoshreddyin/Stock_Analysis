"""
Example usage of Playwright MCP Server for web scraping.
This demonstrates how the News_Analyst subagent can use Playwright tools.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from MCP_Servers.playwright_MCP import (
    navigate_to_url,
    scrape_page_content,
    scrape_news_article,
    extract_links,
    take_screenshot,
    _close_browser
)


async def example_basic_navigation():
    """Example: Navigate to a URL and get basic information"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Basic Navigation")
    print("="*60)
    
    result = await navigate_to_url("https://finance.yahoo.com")
    if result['success']:
        print(f"✓ Successfully navigated to {result['url']}")
        print(f"  Page title: {result['title']}")
        print(f"  HTTP status: {result['status']}")
    else:
        print(f"✗ Navigation failed: {result.get('error')}")


async def example_scrape_content():
    """Example: Scrape page content with optional selector"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Scrape Page Content")
    print("="*60)
    
    # Scrape general content
    result = await scrape_page_content(
        "https://finance.yahoo.com",
        selector="h1, h2, h3"  # Extract only headlines
    )
    
    if result['success']:
        print(f"✓ Successfully scraped {result['url']}")
        print(f"  Page title: {result['title']}")
        print(f"  Content length: {len(result['content'])} characters")
        
        if 'selected_content' in result:
            print(f"  Headlines found: {len(result['selected_content'])}")
            print(f"  First 3 headlines:")
            for i, headline in enumerate(result['selected_content'][:3], 1):
                print(f"    {i}. {headline}")
    else:
        print(f"✗ Scraping failed: {result.get('error')}")


async def example_scrape_news_article():
    """Example: Scrape a news article with intelligent extraction"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Scrape News Article")
    print("="*60)
    
    # This would work with a real news article URL
    article_url = "https://finance.yahoo.com/news/example-stock-article"
    
    result = await scrape_news_article(article_url)
    
    if result['success']:
        print(f"✓ Successfully scraped article from {result['url']}")
        print(f"  Title: {result['title']}")
        print(f"  Author: {result.get('author', 'N/A')}")
        print(f"  Published: {result.get('published_date', 'N/A')}")
        print(f"  Article length: {len(result['article_text'])} characters")
        print(f"  First 200 characters: {result['article_text'][:200]}...")
    else:
        print(f"✗ Article scraping failed: {result.get('error')}")


async def example_extract_links():
    """Example: Extract all links from a page"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Extract Links")
    print("="*60)
    
    result = await extract_links(
        "https://finance.yahoo.com",
        filter_pattern="quote"  # Only links containing "quote"
    )
    
    if result['success']:
        print(f"✓ Successfully extracted links from {result['url']}")
        print(f"  Total filtered links: {result['count']}")
        print(f"  First 3 links:")
        for i, link in enumerate(result['links'][:3], 1):
            print(f"    {i}. {link['text'][:50]}... -> {link['href'][:60]}...")
    else:
        print(f"✗ Link extraction failed: {result.get('error')}")


async def example_take_screenshot():
    """Example: Take a screenshot of a page"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Take Screenshot")
    print("="*60)
    
    result = await take_screenshot(
        "https://finance.yahoo.com",
        full_page=False,
        output_path="/tmp/finance_screenshot.png"
    )
    
    if result['success']:
        print(f"✓ Successfully captured screenshot of {result['url']}")
        print(f"  Screenshot saved to: {result['screenshot_path']}")
        print(f"  Full page: {result['full_page']}")
    else:
        print(f"✗ Screenshot failed: {result.get('error')}")


async def main():
    """Run all examples"""
    print("\n" + "#"*60)
    print("# Playwright MCP Server - Usage Examples")
    print("#"*60)
    print("\nThese examples demonstrate how the News_Analyst subagent")
    print("can use Playwright tools for deep web scraping of news sources.")
    print("\nNote: Some examples may fail due to network restrictions")
    print("in the current environment.")
    
    examples = [
        ("Basic Navigation", example_basic_navigation),
        ("Scrape Content", example_scrape_content),
        ("Scrape News Article", example_scrape_news_article),
        ("Extract Links", example_extract_links),
        ("Take Screenshot", example_take_screenshot),
    ]
    
    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n✗ {name} failed with exception: {str(e)}")
        
        # Small delay between examples
        await asyncio.sleep(1)
    
    # Cleanup
    print("\n" + "="*60)
    print("Cleaning up browser resources...")
    print("="*60)
    await _close_browser()
    
    print("\n✓ Examples complete!")
    print("\nIntegration with DeepAgents:")
    print("  - The News_Analyst subagent now has access to all these tools")
    print("  - It can use internet_search to find news sources")
    print("  - Then use Playwright tools to extract detailed content")
    print("  - This enables deep research analysis of stock news")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        asyncio.run(_close_browser())
