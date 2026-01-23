"""Playwright MCP server (FastMCP style).
- Each function is asynchronous and importable for local scripts.
- The same functions are exposed as MCP tools via `@mcp.tool()`.
- Running this file starts an stdio MCP server.
"""

from __future__ import annotations

import json
import logging
import sys
import asyncio
from typing import Any, Optional
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth
from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("playwright-mcp-server")

# Ensure this module emits logs even when imported into an app that already configured logging.
if not logger.handlers:
    _handler = logging.StreamHandler(stream=sys.stdout)
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)

logger.setLevel(logging.INFO)
logger.propagate = False

# Global browser instance for reuse
_browser: Optional[Browser] = None
_playwright = None
_stealth = Stealth()


async def _get_browser() -> Browser:
    """Get or create a browser instance."""
    global _browser, _playwright
    if _browser is None or not _browser.is_connected():
        logger.info("Launching new browser instance")
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
    return _browser


async def _close_browser():
    """Close the browser instance."""
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


mcp = FastMCP("playwright-mcp-server")


@mcp.tool()
async def navigate_to_url(url: str, wait_for: str = "load") -> dict[str, Any]:
    """
    Navigate to a URL and return basic page information.
    
    Args:
        url: The URL to navigate to
        wait_for: Wait condition - 'load', 'domcontentloaded', 'networkidle' (default: 'load')
    
    Returns:
        dict with url, title, and status
    """
    browser = await _get_browser()
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        await _stealth.apply_stealth_async(page)
        logger.info(f"Navigating to {url}")
        response = await page.goto(url, wait_until=wait_for, timeout=30000)
        
        title = await page.title()
        final_url = page.url
        status = response.status if response else None
        
        result = {
            "url": final_url,
            "title": title,
            "status": status,
            "success": True
        }
        
        await context.close()
        return result
        
    except Exception as e:
        logger.error(f"Error navigating to {url}: {str(e)}")
        await context.close()
        return {
            "url": url,
            "error": str(e),
            "success": False
        }


@mcp.tool()
async def scrape_page_content(
    url: str,
    selector: Optional[str] = None,
    wait_for_selector: Optional[str] = None,
    timeout: int = 30000
) -> dict[str, Any]:
    """
    Scrape content from a web page.
    
    Args:
        url: The URL to scrape
        selector: CSS selector to extract specific content (optional)
        wait_for_selector: Wait for this selector before extracting (optional)
        timeout: Timeout in milliseconds (default: 30000)
    
    Returns:
        dict with url, title, content, and optional selected_content
    """
    browser = await _get_browser()
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        await _stealth.apply_stealth_async(page)
        logger.info(f"Scraping content from {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        
        # Wait for specific selector if provided
        if wait_for_selector:
            await page.wait_for_selector(wait_for_selector, timeout=timeout)
        
        title = await page.title()
        
        # Get full page text content
        full_content = await page.evaluate("""() => {
            // Remove script and style tags
            const scripts = document.querySelectorAll('script, style, noscript');
            scripts.forEach(s => s.remove());
            return document.body.innerText;
        }""")
        
        result = {
            "url": page.url,
            "title": title,
            "content": full_content.strip(),
            "success": True
        }
        
        # Extract specific content if selector provided
        if selector:
            try:
                elements = await page.query_selector_all(selector)
                selected_content = []
                for element in elements:
                    text = await element.inner_text()
                    if text.strip():
                        selected_content.append(text.strip())
                result["selected_content"] = selected_content
            except Exception as e:
                logger.warning(f"Error extracting selector '{selector}': {str(e)}")
                result["selector_error"] = str(e)
        
        await context.close()
        return result
        
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        await context.close()
        return {
            "url": url,
            "error": str(e),
            "success": False
        }


@mcp.tool()
async def scrape_news_article(url: str) -> dict[str, Any]:
    """
    Scrape a news article with intelligent content extraction.
    
    Args:
        url: The URL of the news article
    
    Returns:
        dict with url, title, article_text, published_date, author
    """
    browser = await _get_browser()
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        await _stealth.apply_stealth_async(page)
        logger.info(f"Scraping news article from {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Wait a bit for dynamic content
        await page.wait_for_timeout(2000)
        
        title = await page.title()
        
        # Extract article content using common selectors
        article_data = await page.evaluate("""() => {
            // Common article selectors
            const articleSelectors = [
                'article', '[role="article"]', '.article-content', 
                '.post-content', '.entry-content', 'main article',
                '.article-body', '.story-body', '.content-body'
            ];
            
            let article = null;
            for (const selector of articleSelectors) {
                article = document.querySelector(selector);
                if (article) break;
            }
            
            // Get article text
            let articleText = '';
            if (article) {
                // Remove unwanted elements
                const unwanted = article.querySelectorAll('script, style, nav, header, footer, .ad, .advertisement, aside');
                unwanted.forEach(el => el.remove());
                
                // Get paragraphs
                const paragraphs = article.querySelectorAll('p');
                articleText = Array.from(paragraphs)
                    .map(p => p.innerText.trim())
                    .filter(text => text.length > 50)
                    .join('\\n\\n');
            }
            
            // Try to find publish date
            const dateSelectors = [
                'time', '[datetime]', '.publish-date', '.published-date',
                '.article-date', '.post-date', '.date'
            ];
            let publishDate = null;
            for (const selector of dateSelectors) {
                const elem = document.querySelector(selector);
                if (elem) {
                    publishDate = elem.getAttribute('datetime') || elem.innerText;
                    break;
                }
            }
            
            // Try to find author
            const authorSelectors = [
                '[rel="author"]', '.author', '.by-author', '.article-author',
                '.post-author', '[itemprop="author"]'
            ];
            let author = null;
            for (const selector of authorSelectors) {
                const elem = document.querySelector(selector);
                if (elem) {
                    author = elem.innerText.trim();
                    break;
                }
            }
            
            return {
                articleText: articleText || document.body.innerText,
                publishDate: publishDate,
                author: author
            };
        }""")
        
        result = {
            "url": page.url,
            "title": title,
            "article_text": article_data["articleText"].strip() if article_data["articleText"] else "",
            "published_date": article_data.get("publishDate"),
            "author": article_data.get("author"),
            "success": True
        }
        
        await context.close()
        return result
        
    except Exception as e:
        logger.error(f"Error scraping article {url}: {str(e)}")
        await context.close()
        return {
            "url": url,
            "error": str(e),
            "success": False
        }


@mcp.tool()
async def extract_links(url: str, filter_pattern: Optional[str] = None) -> dict[str, Any]:
    """
    Extract all links from a page.
    
    Args:
        url: The URL to extract links from
        filter_pattern: Optional string pattern to filter links (case-insensitive)
    
    Returns:
        dict with url, links list
    """
    browser = await _get_browser()
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        await _stealth.apply_stealth_async(page)
        logger.info(f"Extracting links from {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        # Extract all links
        links = await page.evaluate("""() => {
            const anchors = document.querySelectorAll('a[href]');
            return Array.from(anchors).map(a => ({
                href: a.href,
                text: a.innerText.trim()
            })).filter(link => link.href && !link.href.startsWith('javascript:'));
        }""")
        
        # Filter links if pattern provided
        if filter_pattern:
            pattern_lower = filter_pattern.lower()
            links = [
                link for link in links 
                if pattern_lower in link["href"].lower() or pattern_lower in link["text"].lower()
            ]
        
        result = {
            "url": page.url,
            "links": links,
            "count": len(links),
            "success": True
        }
        
        await context.close()
        return result
        
    except Exception as e:
        logger.error(f"Error extracting links from {url}: {str(e)}")
        await context.close()
        return {
            "url": url,
            "error": str(e),
            "success": False
        }


@mcp.tool()
async def take_screenshot(url: str, full_page: bool = False, output_path: Optional[str] = None) -> dict[str, Any]:
    """
    Take a screenshot of a web page.
    
    Args:
        url: The URL to screenshot
        full_page: Whether to capture the full scrollable page (default: False)
        output_path: Optional path to save the screenshot (default: auto-generated)
    
    Returns:
        dict with url, screenshot_path, success
    """
    browser = await _get_browser()
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        await _stealth.apply_stealth_async(page)
        logger.info(f"Taking screenshot of {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Generate output path if not provided
        if not output_path:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/tmp/screenshot_{timestamp}.png"
        
        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        await page.screenshot(path=output_path, full_page=full_page)
        
        result = {
            "url": page.url,
            "screenshot_path": output_path,
            "full_page": full_page,
            "success": True
        }
        
        await context.close()
        return result
        
    except Exception as e:
        logger.error(f"Error taking screenshot of {url}: {str(e)}")
        await context.close()
        return {
            "url": url,
            "error": str(e),
            "success": False
        }


if __name__ == "__main__":
    try:
        mcp.run(transport="stdio")
    finally:
        # Cleanup on shutdown
        asyncio.run(_close_browser())

