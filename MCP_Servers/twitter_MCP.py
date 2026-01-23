"""Twitter/X MCP server (FastMCP style).
- Each function is synchronous and importable for local scripts.
- The same functions are exposed as MCP tools via `@mcp.tool()`.
- Running this file starts an stdio MCP server.
"""

from __future__ import annotations

import json
import logging
import sys
import os
from datetime import datetime
from typing import Any, Optional, List, Dict

import tweepy
from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("twitter-mcp-server")

# Ensure this module emits logs even when imported into an app that already configured logging.
if not logger.handlers:
    _handler = logging.StreamHandler(stream=sys.stdout)
    _handler.setLevel(logging.INFO)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)

logger.setLevel(logging.INFO)
logger.propagate = False


def _get_twitter_client() -> tweepy.Client:
    """Get authenticated Twitter API v2 client."""
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        raise RuntimeError("Missing environment variable: TWITTER_BEARER_TOKEN")
    
    return tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True)


def _is_genuine_author(user: Dict[str, Any], min_followers: int = 1000, min_account_age_days: int = 365) -> tuple[bool, str]:
    """
    Determine if a Twitter user is a genuine author based on various metrics.
    
    Args:
        user: User data dictionary
        min_followers: Minimum number of followers required
        min_account_age_days: Minimum account age in days
        
    Returns:
        Tuple of (is_genuine, reason)
    """
    followers_count = user.get("public_metrics", {}).get("followers_count", 0)
    following_count = user.get("public_metrics", {}).get("following_count", 0)
    tweet_count = user.get("public_metrics", {}).get("tweet_count", 0)
    verified = user.get("verified", False)
    
    # Calculate account age
    created_at = user.get("created_at")
    if created_at:
        try:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            account_age_days = (datetime.now(created_date.tzinfo) - created_date).days
        except:
            account_age_days = 0
    else:
        account_age_days = 0
    
    # Verification checks
    reasons = []
    
    # Check verified status (strong indicator)
    if verified:
        return True, "Verified account"
    
    # Check follower count
    if followers_count < min_followers:
        reasons.append(f"Low followers ({followers_count} < {min_followers})")
    
    # Check account age
    if account_age_days < min_account_age_days:
        reasons.append(f"New account ({account_age_days} days < {min_account_age_days})")
    
    # Check follower-to-following ratio (avoid spam/bot accounts)
    if following_count > 0:
        ratio = followers_count / following_count
        if ratio < 0.5 and followers_count < 5000:
            reasons.append(f"Suspicious follower ratio ({ratio:.2f})")
    
    # Check tweet activity
    if tweet_count < 100:
        reasons.append(f"Low tweet activity ({tweet_count} tweets)")
    
    # If no red flags, consider genuine
    if not reasons:
        return True, "Meets all genuinity criteria"
    
    # If many followers despite some issues, still consider genuine
    if followers_count >= 10000:
        return True, f"High follower count ({followers_count}) overrides concerns"
    
    return False, "; ".join(reasons)


mcp = FastMCP("twitter-mcp-server")


@mcp.tool()
def search_tweets(
    query: str,
    max_results: int = 10,
    only_genuine: bool = True,
    min_followers: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Search for tweets on Twitter/X based on query.
    
    Args:
        query: Search query (can include keywords, hashtags, stock symbols)
        max_results: Maximum number of tweets to return (max 100)
        only_genuine: If True, filter tweets from genuine authors only
        min_followers: Minimum followers for genuine author verification
        
    Returns:
        List of tweet objects with author information
    """
    try:
        client = _get_twitter_client()
        
        # Limit max_results to API limit
        max_results = min(max_results, 100)
        
        # Search for tweets
        response = client.search_recent_tweets(
            query=query,
            max_results=max_results,
            tweet_fields=['created_at', 'public_metrics', 'author_id', 'entities', 'referenced_tweets'],
            user_fields=['username', 'name', 'verified', 'public_metrics', 'created_at', 'description'],
            expansions=['author_id']
        )
        
        if not response.data:
            return []
        
        # Create user lookup dict
        users = {}
        if response.includes and 'users' in response.includes:
            for user in response.includes['users']:
                users[user.id] = user.data
        
        results = []
        for tweet in response.data:
            tweet_data = tweet.data
            author_id = tweet_data.get('author_id')
            
            # Get author info
            author = users.get(author_id, {})
            
            # Check if author is genuine
            if only_genuine and author:
                is_genuine, reason = _is_genuine_author(author, min_followers=min_followers)
                if not is_genuine:
                    logger.debug(f"Skipping tweet from @{author.get('username')}: {reason}")
                    continue
            
            # Extract metrics
            public_metrics = tweet_data.get('public_metrics', {})
            
            result = {
                'id': tweet_data.get('id'),
                'text': tweet_data.get('text'),
                'created_at': tweet_data.get('created_at'),
                'author': {
                    'id': author_id,
                    'username': author.get('username'),
                    'name': author.get('name'),
                    'verified': author.get('verified', False),
                    'followers_count': author.get('public_metrics', {}).get('followers_count', 0),
                    'description': author.get('description', ''),
                },
                'metrics': {
                    'retweet_count': public_metrics.get('retweet_count', 0),
                    'reply_count': public_metrics.get('reply_count', 0),
                    'like_count': public_metrics.get('like_count', 0),
                    'quote_count': public_metrics.get('quote_count', 0),
                },
                'url': f"https://twitter.com/{author.get('username')}/status/{tweet_data.get('id')}"
            }
            
            results.append(result)
        
        logger.info(f"Found {len(results)} tweets for query: {query}")
        return results
        
    except Exception as e:
        logger.error(f"Error searching tweets for '{query}': {str(e)}")
        raise RuntimeError(f"Failed to search tweets: {str(e)}")


@mcp.tool()
def search_tweets_by_user(
    username: str,
    max_results: int = 10,
    exclude_replies: bool = True,
    exclude_retweets: bool = True,
) -> List[Dict[str, Any]]:
    """
    Get recent tweets from a specific Twitter/X user.
    
    Args:
        username: Twitter username (without @)
        max_results: Maximum number of tweets to return (max 100)
        exclude_replies: Exclude reply tweets
        exclude_retweets: Exclude retweets
        
    Returns:
        List of tweet objects from the user
    """
    try:
        client = _get_twitter_client()
        
        # Get user ID
        user = client.get_user(username=username, user_fields=['id', 'username', 'name', 'verified', 'public_metrics', 'created_at', 'description'])
        if not user.data:
            return []
        
        user_data = user.data.data
        user_id = user_data.get('id')
        
        # Build query options
        max_results = min(max_results, 100)
        
        # Get user's tweets
        response = client.get_users_tweets(
            id=user_id,
            max_results=max_results,
            tweet_fields=['created_at', 'public_metrics', 'entities', 'referenced_tweets'],
            exclude=['replies'] if exclude_replies else None,
        )
        
        if not response.data:
            return []
        
        results = []
        for tweet in response.data:
            tweet_data = tweet.data
            
            # Check if it's a retweet
            if exclude_retweets:
                referenced_tweets = tweet_data.get('referenced_tweets', [])
                if any(ref.get('type') == 'retweeted' for ref in referenced_tweets):
                    continue
            
            public_metrics = tweet_data.get('public_metrics', {})
            
            result = {
                'id': tweet_data.get('id'),
                'text': tweet_data.get('text'),
                'created_at': tweet_data.get('created_at'),
                'author': {
                    'id': user_id,
                    'username': user_data.get('username'),
                    'name': user_data.get('name'),
                    'verified': user_data.get('verified', False),
                    'followers_count': user_data.get('public_metrics', {}).get('followers_count', 0),
                    'description': user_data.get('description', ''),
                },
                'metrics': {
                    'retweet_count': public_metrics.get('retweet_count', 0),
                    'reply_count': public_metrics.get('reply_count', 0),
                    'like_count': public_metrics.get('like_count', 0),
                    'quote_count': public_metrics.get('quote_count', 0),
                },
                'url': f"https://twitter.com/{user_data.get('username')}/status/{tweet_data.get('id')}"
            }
            
            results.append(result)
        
        logger.info(f"Found {len(results)} tweets from @{username}")
        return results
        
    except Exception as e:
        logger.error(f"Error fetching tweets from @{username}: {str(e)}")
        raise RuntimeError(f"Failed to fetch user tweets: {str(e)}")


@mcp.tool()
def get_user_info(username: str) -> Dict[str, Any]:
    """
    Get information about a Twitter/X user.
    
    Args:
        username: Twitter username (without @)
        
    Returns:
        User information including metrics and genuinity status
    """
    try:
        client = _get_twitter_client()
        
        user = client.get_user(
            username=username,
            user_fields=['id', 'username', 'name', 'verified', 'public_metrics', 'created_at', 'description', 'profile_image_url']
        )
        
        if not user.data:
            return {"error": "User not found"}
        
        user_data = user.data.data
        
        # Check genuinity
        is_genuine, reason = _is_genuine_author(user_data)
        
        result = {
            'id': user_data.get('id'),
            'username': user_data.get('username'),
            'name': user_data.get('name'),
            'description': user_data.get('description', ''),
            'verified': user_data.get('verified', False),
            'created_at': user_data.get('created_at'),
            'profile_image_url': user_data.get('profile_image_url'),
            'public_metrics': user_data.get('public_metrics', {}),
            'genuinity': {
                'is_genuine': is_genuine,
                'reason': reason
            }
        }
        
        logger.info(f"Retrieved info for @{username}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching user info for @{username}: {str(e)}")
        raise RuntimeError(f"Failed to fetch user info: {str(e)}")


if __name__ == "__main__":
    mcp.run(transport="stdio")
