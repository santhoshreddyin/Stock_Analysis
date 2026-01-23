# Vector and Graph Database for News Analysis

This document describes the Vector Database (for RAG - Retrieval-Augmented Generation) and Graph Database implementation for News Analysis in the Stock Analysis system.

## Overview

The system now includes:
- **Vector Database**: Stores news articles with semantic embeddings for intelligent search
- **Graph Database**: Models relationships between entities (companies, people, events, topics)
- **News Summaries**: Aggregated summaries with sentiment analysis
- **Frontend Visualization**: Interactive graph visualization and news display

## Architecture

### Database Models

#### 1. NewsArticle
Stores news articles with vector embeddings for semantic search.

```python
- article_id: Unique identifier
- symbol: Stock symbol
- title: Article title
- content: Full content
- source: News source (Twitter, Web, Bloomberg, etc.)
- embedding: 384-dimensional vector for semantic search
- sentiment_score: -1 (negative) to 1 (positive)
- published_date: Publication date
```

#### 2. GraphEntity
Represents nodes in the graph (companies, people, events, topics).

```python
- entity_id: Unique identifier
- entity_type: company, person, event, topic
- name: Entity name
- symbol: Stock symbol (for companies)
- embedding: Vector embedding for entity similarity
- mention_count: How many times mentioned
```

#### 3. GraphRelationship
Represents edges connecting entities.

```python
- source_entity_id: Source entity
- target_entity_id: Target entity
- relationship_type: mentions, affects, competes_with, etc.
- weight: Relationship strength
- context: Context of the relationship
```

#### 4. NewsSummary
Aggregated summaries of news analysis.

```python
- symbol: Stock symbol
- period: daily, weekly, monthly
- summary_text: Summary content
- key_events: List of key events
- sentiment_trend: positive, negative, neutral, mixed
- overall_sentiment_score: Average sentiment
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

New dependencies:
- `pgvector`: PostgreSQL extension for vector operations
- `sentence-transformers`: For generating text embeddings

### 2. Initialize Database

The database initialization script creates all necessary tables and enables the pgvector extension:

```bash
python init_news_graph_db.py
```

This will:
- Enable the pgvector extension in PostgreSQL
- Create all news and graph database tables
- Display a summary of created tables

### 3. Configure PostgreSQL

Make sure you have PostgreSQL with the pgvector extension installed:

```bash
# Ubuntu/Debian
sudo apt install postgresql-server-dev-all
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# macOS (with Homebrew)
brew install pgvector
```

Set environment variables:
```bash
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="postgres"
export DB_USER="postgres"
export DB_PASSWORD="postgres"
```

## Usage

### News Analyst Integration

The News_Analyst agent now automatically saves collected news to the database. It has two new tools:

1. **save_news_to_database**: Stores news articles with embeddings and entity extraction
2. **create_news_summary**: Creates aggregated summaries

Example usage in the agent:
```python
# The News_Analyst will automatically use these tools
python DeepAgents.py --prompt "Analyse AAPL stock"
```

### API Endpoints

#### Get News Articles
```bash
GET /api/news?symbol=AAPL&limit=20
```

#### Semantic Search
```bash
POST /api/news/search
{
  "query": "earnings report",
  "symbol": "AAPL",
  "limit": 10
}
```

#### Get News Summaries
```bash
GET /api/news/summary/AAPL?period=daily&limit=5
```

#### Get Graph Data
```bash
GET /api/graph?symbol=AAPL&limit=100
```

### Frontend Components

#### Graph Visualization
Navigate to **Entity Graph** tab to see:
- Interactive force-directed graph
- Nodes colored by entity type (company, person, event, topic)
- Edges showing relationships between entities
- Click on nodes for detailed information

#### News Analysis
Navigate to **News Analysis** tab to see:
- List of collected news articles with sentiment scores
- Aggregated news summaries
- Key events and sentiment trends
- Filter by stock symbol

## Features

### Vector Database (RAG)

The vector database enables:
- **Semantic Search**: Find relevant news articles based on meaning, not just keywords
- **Similarity Matching**: Discover related articles and entities
- **Context Retrieval**: Retrieve relevant context for LLM queries

### Graph Database

The graph database provides:
- **Entity Relationships**: Map connections between companies, people, and events
- **Impact Analysis**: Understand how events affect different entities
- **Network Visualization**: See the complete relationship network
- **Pattern Discovery**: Identify important entities and relationships

### Sentiment Analysis

Each news article includes:
- Sentiment score (-1 to 1)
- Overall sentiment trend
- Per-entity sentiment tracking
- Historical sentiment tracking

## Data Flow

```
News Collection (News_Analyst)
    ↓
Entity Extraction & Embedding Generation
    ↓
Vector Database Storage (NewsArticle)
    ↓
Graph Construction (GraphEntity, GraphRelationship)
    ↓
Summary Generation (NewsSummary)
    ↓
API Endpoints
    ↓
Frontend Visualization
```

## Technical Details

### Embedding Model

We use `all-MiniLM-L6-v2` from sentence-transformers:
- Dimension: 384
- Fast inference
- Good quality for English text
- Runs locally (no API costs)

For production, you may want to use:
- OpenAI embeddings (1536 dimensions)
- Larger models for better quality
- Domain-specific models for financial text

### Entity Extraction

Current implementation uses simple pattern matching:
- Stock symbols ($AAPL, MSFT)
- Financial terms (earnings, merger, etc.)

For production, consider using:
- spaCy NER (Named Entity Recognition)
- FinBERT for financial entity extraction
- Custom NER models trained on financial data

### Graph Queries

Example queries you can run:

```python
# Find all entities related to a stock
session.query(GraphEntity).filter(
    GraphEntity.symbol == 'AAPL'
).all()

# Find all relationships
session.query(GraphRelationship).filter(
    GraphRelationship.relationship_type == 'affects'
).all()

# Semantic search for news
news_service.semantic_search(
    session=session,
    query="What caused the stock price to drop?",
    symbol="AAPL"
)
```

## Future Enhancements

Potential improvements:
1. Use advanced NLP models for entity extraction
2. Implement graph algorithms (PageRank, community detection)
3. Add temporal analysis (how relationships change over time)
4. Implement knowledge graph reasoning
5. Add more relationship types
6. Integrate with external knowledge bases
7. Add real-time news streaming
8. Implement alert system based on graph patterns

## Troubleshooting

### pgvector Extension Not Found
```bash
# Make sure pgvector is installed in PostgreSQL
sudo apt install postgresql-15-pgvector  # Ubuntu/Debian
brew install pgvector  # macOS
```

### Model Download Issues
The sentence-transformers model is downloaded on first use (~100MB). Ensure you have:
- Internet connection
- Sufficient disk space
- Write permissions in the cache directory

### Database Connection Issues
Check:
- PostgreSQL is running
- Environment variables are set correctly
- Database exists and user has permissions
- pgvector extension is enabled

## Performance Considerations

- **Embeddings**: Generated once per article, cached in database
- **Graph Queries**: Use indexes on entity_id, symbol, relationship_type
- **Vector Search**: Uses pgvector's HNSW index for fast similarity search
- **Batch Processing**: Process multiple articles in batches for better performance

## Security

- Never store API keys in the database
- Validate all user input
- Use parameterized queries
- Implement rate limiting on API endpoints
- Sanitize HTML content from news sources
- Regular security audits with CodeQL

## Support

For issues or questions:
- Check logs in the application
- Review API error responses
- Test database connectivity
- Verify environment variables

## License

Same as the main Stock Analysis project.
