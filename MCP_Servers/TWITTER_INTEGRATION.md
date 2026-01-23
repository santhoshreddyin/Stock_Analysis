# Twitter/X Integration for Stock Analysis

## Overview

This integration enables the News Analyst sub-agent to search and analyze tweets from Twitter/X (formerly Twitter) to gather real-time sentiment and news about stocks from genuine, credible sources.

## Features

### 1. **Tweet Search with Genuinity Filtering**
- Search for tweets about stocks, companies, or financial topics
- Automatically filter tweets from genuine authors based on:
  - Follower count (default minimum: 1,000 followers)
  - Account age (default minimum: 1 year)
  - Verification status
  - Tweet activity
  - Follower-to-following ratio

### 2. **User-Specific Tweet Retrieval**
- Get recent tweets from specific Twitter users
- Exclude replies and retweets for cleaner results
- Useful for tracking known financial experts and analysts

### 3. **User Profile Analysis**
- Get detailed information about Twitter users
- Verify author credibility before trusting their insights
- Check verification status, follower metrics, and account age

## Setup

### Prerequisites

1. **Twitter API Access**: You need a Twitter Developer account with API v2 access
   - Sign up at: https://developer.twitter.com
   - Create a project and app
   - Generate a Bearer Token

2. **Environment Variable**: Set your Twitter Bearer Token
   ```bash
   export TWITTER_BEARER_TOKEN="your_bearer_token_here"
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Available Tools

### `search_tweets(query, max_results=10, only_genuine=True, min_followers=1000)`

Search for tweets based on a query with automatic genuinity filtering.

**Parameters:**
- `query` (str): Search query (keywords, hashtags, stock symbols like "$AAPL")
- `max_results` (int): Maximum number of tweets to return (max 100)
- `only_genuine` (bool): Filter for genuine authors only (default: True)
- `min_followers` (int): Minimum followers for genuine verification (default: 1000)

**Example Queries:**
- `"$TSLA stock"` - Search for Tesla stock tweets
- `"#stocks OR #trading"` - Search for general stock market tweets
- `"AAPL earnings"` - Search for Apple earnings-related tweets

**Returns:**
- List of tweet objects with:
  - Tweet text and metadata
  - Author information (username, followers, verification status)
  - Engagement metrics (likes, retweets, replies)
  - Direct URL to tweet

### `search_tweets_by_user(username, max_results=10, exclude_replies=True, exclude_retweets=True)`

Get recent tweets from a specific user.

**Parameters:**
- `username` (str): Twitter username (without @)
- `max_results` (int): Maximum tweets to return (max 100)
- `exclude_replies` (bool): Exclude reply tweets (default: True)
- `exclude_retweets` (bool): Exclude retweets (default: True)

**Example:**
```python
# Get tweets from a financial analyst
search_tweets_by_user("jimcramer", max_results=10)
```

### `get_user_info(username)`

Get detailed information about a Twitter user including genuinity assessment.

**Parameters:**
- `username` (str): Twitter username (without @)

**Returns:**
- User profile with:
  - Basic info (name, username, description)
  - Public metrics (followers, following, tweet count)
  - Verification status
  - Account creation date
  - Genuinity assessment with reason

## Genuinity Verification Logic

The system evaluates Twitter users based on multiple factors:

### ✅ Automatically Genuine:
- **Verified accounts** (blue checkmark)
- **10,000+ followers** (regardless of other metrics)

### 📊 Evaluated Criteria:
1. **Follower Count**: Minimum 1,000 followers (configurable)
2. **Account Age**: Minimum 365 days old
3. **Follower-to-Following Ratio**: Must be > 0.5 for accounts with < 5,000 followers
4. **Tweet Activity**: Minimum 100 tweets

### ❌ Filtered Out:
- New accounts (< 1 year old)
- Low follower counts (< 1,000)
- Suspicious follower ratios (potential spam/bots)
- Inactive accounts (< 100 tweets)

## Usage in News Analyst

When the News Analyst sub-agent is called, it automatically has access to Twitter tools (if configured). Example usage:

```python
# The agent can now search for stock-related tweets
"Search Twitter for recent sentiment about NVDA stock from credible sources"

# Or get tweets from specific financial experts
"Get the latest tweets from financial analyst @jimcramer about tech stocks"

# Or verify a user's credibility
"Check if @user123 is a credible source for financial information"
```

## Best Practices

1. **Focus on Verified Sources**: Prioritize verified accounts and high-follower users
2. **Cross-Reference**: Always cross-reference Twitter sentiment with traditional news sources
3. **Check Engagement**: High engagement (likes, retweets) often indicates important tweets
4. **Monitor Known Experts**: Track tweets from known financial journalists, analysts, and company executives
5. **Use Specific Queries**: More specific queries yield better results (e.g., "$AAPL earnings Q4" vs just "Apple")

## Limitations

1. **Rate Limits**: Twitter API has rate limits. The client automatically waits on rate limits.
2. **Recent Tweets Only**: API v2 basic access provides tweets from the last 7 days
3. **No Historical Data**: Cannot search tweets older than 7 days without elevated access
4. **Authentication Required**: Must have valid TWITTER_BEARER_TOKEN set

## Troubleshooting

### "Missing environment variable: TWITTER_BEARER_TOKEN"
**Solution**: Set the environment variable with your Twitter Bearer Token

### "Twitter tools will not be available"
**Warning**: This appears if TWITTER_BEARER_TOKEN is not set. The agent will still work but without Twitter functionality.

### Rate Limit Errors
**Solution**: The client automatically waits on rate limits. If you consistently hit limits, consider upgrading your Twitter API access tier.

## Security Notes

- **Never commit** your Bearer Token to version control
- Use environment variables or secure secret management
- Rotate tokens periodically for security
- Monitor your API usage in the Twitter Developer Portal

## Integration Architecture

```
DeepAgents.py
    ↓
News_Analyst Sub-Agent
    ↓
[internet_search] + [Twitter MCP Tools]
    ↓
twitter_MCP.py (FastMCP Server)
    ↓
Tweepy Client → Twitter API v2
```

## Example Output

```json
{
  "id": "1234567890",
  "text": "$NVDA breaking new highs! Strong earnings report...",
  "created_at": "2024-01-15T10:30:00Z",
  "author": {
    "username": "techanalyst",
    "name": "Tech Analyst",
    "verified": true,
    "followers_count": 50000
  },
  "metrics": {
    "retweet_count": 150,
    "like_count": 500,
    "reply_count": 45
  },
  "url": "https://twitter.com/techanalyst/status/1234567890"
}
```

## Contributing

When extending the Twitter integration:
1. Follow the existing MCP server pattern
2. Add appropriate error handling
3. Log all API interactions
4. Consider rate limits
5. Update this documentation
