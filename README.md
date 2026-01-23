# Stock Analysis with AI Agents

An intelligent stock analysis system powered by AI agents that provides comprehensive fundamental, technical, and news analysis of stocks.

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended for Development)
```bash
# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker compose up -d

# Access the application
# Frontend: http://localhost
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Kubernetes (Production Deployment)
```bash
# See QUICKSTART.md for detailed instructions
cd k8s
./deploy.sh
```

📚 **Full deployment guides**: [QUICKSTART.md](QUICKSTART.md) | [CICD_DOCUMENTATION.md](CICD_DOCUMENTATION.md)

## Features

### Multi-Agent Analysis System

The system uses specialized AI sub-agents to analyze stocks from different perspectives:

1. **Technical Analyst** - Analyzes technical indicators, support/resistance levels, moving averages, share holding patterns, PE ratios, and insider trading
2. **Fundamental Analyst** - Evaluates industry trends, competitive moat, competitors, financial health, and management effectiveness
3. **News Analyst** - Gathers and analyzes the latest news from multiple sources including:
   - Web search (via Tavily)
   - **Twitter/X integration** for real-time sentiment and news from genuine sources
4. **User Notifier** - Compiles analysis into professional HTML reports and sends them via email

### Twitter/X Integration (New!)

The News Analyst can now research tweets from credible sources to gather real-time market sentiment and breaking news. Features include:

- **Automatic Genuinity Filtering** - Only includes tweets from verified or credible authors based on:
  - Follower count (default minimum: 1,000)
  - Account age (minimum 1 year)
  - Verification status
  - Tweet activity and follower ratios
- **Flexible Search** - Search by stock symbols, hashtags, keywords, or specific users
- **User Verification** - Check author credibility before trusting insights
- **Engagement Metrics** - Track likes, retweets, and replies to gauge tweet importance

See [MCP_Servers/TWITTER_INTEGRATION.md](MCP_Servers/TWITTER_INTEGRATION.md) for detailed documentation.

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database (for stock data caching)
- OpenAI API key
- Tavily API key
- Gmail account with App Password (for email notifications)
- Twitter Bearer Token (optional, for Twitter integration)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/santhoshreddyin/Stock_Analysis.git
cd Stock_Analysis
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY="your_openai_api_key"
export TAVILY_API_KEY="your_tavily_api_key"
export GMAIL_SMTP_USER="your_gmail@gmail.com"
export GMAIL_APP_PASSWORD="your_16_char_app_password"

# Optional: for Twitter integration
export TWITTER_BEARER_TOKEN="your_twitter_bearer_token"
```

### Twitter API Setup (Optional)

To enable Twitter/X integration:

1. Sign up for a Twitter Developer account at https://developer.twitter.com
2. Create a project and app
3. Generate a Bearer Token
4. Set the environment variable: `export TWITTER_BEARER_TOKEN="your_token"`

See [MCP_Servers/TWITTER_INTEGRATION.md](MCP_Servers/TWITTER_INTEGRATION.md) for detailed setup instructions.

## Usage

### Basic Stock Analysis

Analyze a stock using the command-line interface:

```bash
python DeepAgents.py --prompt "Analyse AAPL stock"
```

The system will:
1. Gather technical data using yfinance
2. Perform fundamental analysis
3. Search for recent news (web + Twitter if configured)
4. Compile a comprehensive report
5. Send the report via email

### Using Twitter Integration

If Twitter is configured, the News Analyst will automatically search for relevant tweets. Example prompts:

```bash
# General stock analysis (includes Twitter sentiment)
python DeepAgents.py --prompt "Analyse TSLA stock"

# Focus on news and sentiment
python DeepAgents.py --prompt "What's the latest news and Twitter sentiment about NVDA?"
```

### Testing Twitter Integration

Run the example script to test Twitter functionality:

```bash
python MCP_Servers/twitter_example.py
```

This will demonstrate:
- Searching for stock-related tweets
- Checking user credibility
- Getting tweets from specific financial analysts

## Architecture

```
DeepAgents.py (Main Orchestrator)
    ↓
┌─────────────────────────────────────────┐
│  Sub-Agents (Specialized Analysts)       │
├─────────────────────────────────────────┤
│  • Technical_Analyst                    │
│  • Fundamental_Analyst                  │
│  • News_Analyst                         │
│  • User_Notifier                        │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  Tools & Data Sources                    │
├─────────────────────────────────────────┤
│  • yfinance_MCP (Stock data)            │
│  • twitter_MCP (Social sentiment)        │
│  • internet_search (Web news)            │
│  • Gmail SMTP (Notifications)            │
└─────────────────────────────────────────┘
```

## MCP Servers

The system uses Model Context Protocol (MCP) servers to provide tools to agents:

- **yfinance_MCP.py** - Stock market data via Yahoo Finance
- **twitter_MCP.py** - Twitter/X integration for social sentiment (NEW!)

## Data Storage

- **AgentMemory/** - Stores analysis reports and agent notes
- **PostgreSQL Database** - Caches historical stock data for faster retrieval

## Deployment & CI/CD

### GitHub Actions Pipeline

This project includes a complete CI/CD pipeline for automated deployment:

- **CI Workflow**: Automated linting, testing, and security scanning
- **CD Workflow**: Docker image building and Kubernetes deployment
- **Local K8s**: Support for deployment to local Kubernetes clusters

### Deployment Options

1. **Docker Compose** - Quick local development setup
2. **Kubernetes** - Production-ready deployment with:
   - Auto-scaling backend and frontend
   - StatefulSet PostgreSQL with persistent storage
   - Nginx Ingress for routing
   - Health checks and resource limits

📚 **Deployment Documentation**:
- [Quick Start Guide](QUICKSTART.md) - Get up and running in minutes
- [CI/CD Documentation](CICD_DOCUMENTATION.md) - Complete pipeline guide
- [Kubernetes Guide](k8s/README.md) - K8s deployment details

## Configuration

Key environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for AI models |
| `TAVILY_API_KEY` | Yes | Tavily API key for web search |
| `GMAIL_SMTP_USER` | Yes | Gmail address for sending reports |
| `GMAIL_APP_PASSWORD` | Yes | Gmail app password (16 characters) |
| `TWITTER_BEARER_TOKEN` | No | Twitter API bearer token |
| `OPENAI_MODEL` | No | OpenAI model to use (default: gpt-5-nano) |
| `OPENAI_MAX_TOKENS` | No | Max tokens per request (default: 6000) |

Copy `.env.example` to `.env` and fill in your values.

## Security

- Never commit API keys or tokens to version control
- Use environment variables or secure secret management (e.g., Kubernetes Secrets)
- Rotate API tokens periodically
- Monitor API usage in respective dashboards
- Security scanning included in CI pipeline (Trivy)

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/santhoshreddyin/Stock_Analysis/issues)
- Documentation: See markdown files in `MCP_Servers/` directory

## Acknowledgments

- Built with [LangChain](https://langchain.com/)
- Uses [DeepAgents](https://github.com/JoshuaC215/deepagents) framework
- Market data from [yfinance](https://github.com/ranaroussi/yfinance)
- Social data from [Twitter API](https://developer.twitter.com/)
- Web search via [Tavily](https://tavily.com/)
