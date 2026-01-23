# Quick Start Guide: Vector & Graph Database

Get the Vector and Graph Database for News Analysis up and running in minutes.

## Prerequisites

- Python 3.8+
- PostgreSQL 15+ with pgvector extension
- Node.js 18+ (for frontend)
- Git

## Installation Steps

### 1. Install PostgreSQL and pgvector

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-server-dev-all
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

**macOS:**
```bash
brew install postgresql@15
brew install pgvector
```

### 2. Setup Database

```bash
# Start PostgreSQL
sudo service postgresql start  # Linux
brew services start postgresql@15  # macOS

# Create database and enable extension
psql -U postgres
CREATE DATABASE stock_analysis;
\c stock_analysis
CREATE EXTENSION vector;
\q
```

### 3. Configure Environment Variables

```bash
# Database configuration
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="stock_analysis"
export DB_USER="postgres"
export DB_PASSWORD="your_password"

# API Keys (if not already set)
export OPENAI_API_KEY="your_openai_key"
export TAVILY_API_KEY="your_tavily_key"
export GMAIL_SMTP_USER="your_email@gmail.com"
export GMAIL_APP_PASSWORD="your_app_password"
```

### 4. Install Python Dependencies

```bash
cd Stock_Analysis
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
python init_news_graph_db.py
```

Expected output:
```
✓ Connected to database: stock_analysis
✓ pgvector extension enabled
✓ All tables created successfully!
```

### 6. Run Tests (Optional but Recommended)

```bash
python test_vector_graph_db.py
```

Expected output:
```
🎉 All tests passed!
```

### 7. Start the API Server

```bash
cd api
python main.py
```

API will be available at: `http://localhost:8000`

### 8. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at: `http://localhost:5173`

## Verify Installation

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/api/health

# List endpoints
curl http://localhost:8000/

# Get news articles (will be empty initially)
curl http://localhost:8000/api/news

# Get graph data (will be empty initially)
curl http://localhost:8000/api/graph
```

### Test News Collection

Run the agent to collect news:

```bash
python DeepAgents.py --prompt "Analyze AAPL stock"
```

The News_Analyst will:
1. Collect news from web and Twitter
2. Save articles to database with embeddings
3. Extract entities and create graph
4. Calculate sentiment scores
5. Create summaries

### View Results in Frontend

1. Open browser to `http://localhost:5173`
2. Navigate to "Entity Graph" tab
3. Navigate to "News Analysis" tab
4. Select a stock symbol to view its news

## Quick Usage Example

### Collecting News Data

```bash
# Analyze a stock - this will collect and store news
python DeepAgents.py --prompt "Analyze TSLA stock"

# Wait for the analysis to complete
# The News_Analyst will automatically save data to the database
```

### Querying via API

```bash
# Get news articles for a symbol
curl "http://localhost:8000/api/news?symbol=TSLA&limit=10"

# Semantic search
curl -X POST "http://localhost:8000/api/news/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "earnings report", "symbol": "TSLA", "limit": 5}'

# Get news summary
curl "http://localhost:8000/api/news/summary/TSLA?period=daily"

# Get graph data
curl "http://localhost:8000/api/graph?symbol=TSLA&limit=50"
```

### Using the Frontend

1. **Dashboard**: Overview of stock data
2. **Stock List**: Browse available stocks
3. **Entity Graph**: Interactive visualization of entities and relationships
   - See companies, topics, events as nodes
   - View relationships as edges
   - Click nodes for details
4. **News Analysis**: View news articles and summaries
   - Filter by stock symbol
   - View sentiment scores
   - Read full articles
   - See aggregated summaries

## Troubleshooting

### Database Connection Failed

```bash
# Check PostgreSQL is running
sudo service postgresql status

# Check environment variables
echo $DB_HOST
echo $DB_NAME
echo $DB_USER

# Test connection manually
psql -h localhost -U postgres -d stock_analysis
```

### pgvector Extension Not Found

```bash
# Verify extension is installed
psql -U postgres -d stock_analysis -c "SELECT * FROM pg_available_extensions WHERE name='vector';"

# If not found, install pgvector (see step 1)
```

### Model Download Issues

The sentence-transformers model downloads on first use (~100MB).

```bash
# Pre-download the model
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Frontend Not Loading

```bash
# Check if API is running
curl http://localhost:8000/api/health

# Check CORS configuration in api/main.py
# Make sure port 5173 is in allow_origins

# Rebuild frontend
cd frontend
rm -rf node_modules dist
npm install
npm run dev
```

### No Data Showing

This is expected if you haven't run any analysis yet.

```bash
# Run analysis to collect data
python DeepAgents.py --prompt "Analyze AAPL stock"

# Wait for completion, then refresh frontend
```

## Architecture Overview

```
User → Frontend (React) → API (FastAPI) → Database (PostgreSQL + pgvector)
                            ↑
                            |
                    News_Analyst Agent
                    (Collects & Stores)
```

## Next Steps

1. **Collect Data**: Run analysis on multiple stocks
   ```bash
   python DeepAgents.py --prompt "Analyze MSFT stock"
   python DeepAgents.py --prompt "Analyze GOOGL stock"
   ```

2. **Explore Visualization**: View the entity graph and news summaries

3. **Test Semantic Search**: Use the search endpoint to find relevant news

4. **Review Documentation**:
   - `README_VECTOR_GRAPH_DB.md` - Detailed documentation
   - `ARCHITECTURE.md` - System architecture
   - `IMPLEMENTATION_SUMMARY.md` - Implementation details

## Development

### Running in Development Mode

```bash
# Backend with auto-reload
cd api
uvicorn main:app --reload --port 8000

# Frontend with hot reload
cd frontend
npm run dev
```

### Running Tests

```bash
# Test database and services
python test_vector_graph_db.py

# Test API endpoints
cd api
pytest  # If you have pytest configured
```

## Production Deployment

For production deployment:

1. Set up proper PostgreSQL instance
2. Configure environment variables securely
3. Use production WSGI server (gunicorn)
4. Build frontend for production (`npm run build`)
5. Set up reverse proxy (nginx)
6. Enable HTTPS
7. Configure logging and monitoring
8. Set up automated backups

See `IMPLEMENTATION_SUMMARY.md` for production recommendations.

## Support

- **Documentation**: Check README_VECTOR_GRAPH_DB.md
- **Tests**: Run test_vector_graph_db.py
- **Logs**: Check console output for errors
- **Issues**: Create a GitHub issue with error details

## Success!

If you've completed all steps, you should now have:

✅ PostgreSQL database with pgvector
✅ Initialized tables and models
✅ Running API server
✅ Running frontend application
✅ Ability to collect and visualize news data

Start analyzing stocks to see the system in action!

```bash
python DeepAgents.py --prompt "Analyze your favorite stock"
```
