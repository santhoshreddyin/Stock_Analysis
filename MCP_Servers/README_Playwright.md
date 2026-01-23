# Playwright MCP Server for Web Scraping

This MCP (Model Context Protocol) server provides web scraping capabilities using Playwright for the Stock Analysis system. It's specifically designed to enable the News_Analyst subagent to perform deep research analysis by scraping news sources.

## Features

The Playwright MCP Server provides the following tools:

### 1. `navigate_to_url`
Navigate to a URL and return basic page information.

**Parameters:**
- `url` (str): The URL to navigate to
- `wait_for` (str, optional): Wait condition - 'load', 'domcontentloaded', 'networkidle' (default: 'load')

**Returns:**
- Dictionary with url, title, status, and success flag

### 2. `scrape_page_content`
Scrape content from a web page with optional CSS selector filtering.

**Parameters:**
- `url` (str): The URL to scrape
- `selector` (str, optional): CSS selector to extract specific content
- `wait_for_selector` (str, optional): Wait for this selector before extracting
- `timeout` (int, optional): Timeout in milliseconds (default: 30000)

**Returns:**
- Dictionary with url, title, full content, and optionally selected_content

### 3. `scrape_news_article`
Intelligently scrape a news article with automatic content detection.

**Parameters:**
- `url` (str): The URL of the news article

**Returns:**
- Dictionary with url, title, article_text, published_date, author, and success flag

### 4. `extract_links`
Extract all links from a page with optional filtering.

**Parameters:**
- `url` (str): The URL to extract links from
- `filter_pattern` (str, optional): String pattern to filter links (case-insensitive)

**Returns:**
- Dictionary with url, links list (with href and text), count, and success flag

### 5. `take_screenshot`
Take a screenshot of a web page.

**Parameters:**
- `url` (str): The URL to screenshot
- `full_page` (bool, optional): Whether to capture full scrollable page (default: False)
- `output_path` (str, optional): Path to save screenshot (default: auto-generated)

**Returns:**
- Dictionary with url, screenshot_path, full_page flag, and success flag

## Integration with DeepAgents

The Playwright MCP Server is integrated with the `DeepAgents.py` file and provides tools to the **News_Analyst** subagent. The News_Analyst can now:

1. Use `internet_search` to find relevant news sources
2. Use Playwright tools to extract detailed content from those sources
3. Scrape full articles using `scrape_news_article`
4. Extract specific content using `scrape_page_content` with CSS selectors
5. Follow links and navigate complex news sites

## Architecture

The server follows the FastMCP pattern used in the repository:
- Uses async/await for non-blocking operations
- Reuses browser instances for efficiency
- Implements stealth mode to avoid detection
- Provides both tool functions and MCP server functionality
- Clean error handling and logging

## Browser Configuration

The server uses Chromium in headless mode with:
- Stealth mode enabled (playwright-stealth)
- Realistic user agent strings
- No sandbox mode for compatibility
- Automatic resource cleanup

## Usage Example

See `Samples/playwright_examples.py` for comprehensive usage examples.

```python
from MCP_Servers.playwright_MCP import scrape_news_article

result = await scrape_news_article("https://finance.yahoo.com/news/article")
if result['success']:
    print(f"Title: {result['title']}")
    print(f"Article: {result['article_text']}")
```

## Running as MCP Server

The server can be run as a standalone MCP server:

```bash
python MCP_Servers/playwright_MCP.py
```

Or it can be integrated into the multi-server setup in `DeepAgents.py` (already configured).

## Dependencies

- `playwright` - Browser automation library
- `playwright-stealth` - Stealth mode for avoiding detection
- `mcp` - Model Context Protocol server
- `fastmcp` - FastMCP for tool definition

All dependencies are listed in `requirements.txt`.

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## Error Handling

All tools return a dictionary with:
- `success`: Boolean indicating if the operation succeeded
- `error`: Error message if operation failed
- Other relevant data fields based on the tool

This allows the News_Analyst to gracefully handle failures and retry or use alternative sources.

## Future Enhancements

Possible improvements:
- Add support for authenticated sessions
- Implement cookie management
- Add proxy support
- Support for JavaScript-heavy sites with extended wait times
- PDF extraction from articles
- Image downloading and analysis
- Multi-page scraping workflows
