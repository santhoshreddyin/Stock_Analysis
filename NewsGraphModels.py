"""
News Analysis Database Models with Vector and Graph Support
Implements RAG (Retrieval-Augmented Generation) and Graph Database capabilities
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime
from typing import Optional
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class NewsArticle(Base):
    """
    News articles with vector embeddings for semantic search (RAG)
    Stores news data collected by the News_Analyst agent
    """
    __tablename__ = 'news_articles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(255), unique=True, nullable=False, index=True)
    symbol = Column(String(15), nullable=False, index=True)  # Stock symbol
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(255))  # e.g., "Twitter", "Web", "Bloomberg"
    url = Column(Text)
    author = Column(String(255))
    published_date = Column(DateTime, nullable=False, index=True)
    collected_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Vector embedding for semantic search (1536 dimensions for OpenAI embeddings)
    embedding = Column(Vector(1536))
    
    # Sentiment and relevance scores
    sentiment_score = Column(Float)  # -1 (negative) to 1 (positive)
    relevance_score = Column(Float)  # 0 to 1
    
    # Metadata
    metadata = Column(JSON)  # Store additional metadata like tweet metrics, etc.
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_symbol_date', 'symbol', 'published_date'),
        Index('idx_source_date', 'source', 'published_date'),
    )


class GraphEntity(Base):
    """
    Graph database nodes representing entities (companies, people, events, topics)
    """
    __tablename__ = 'graph_entities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_id = Column(String(255), unique=True, nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)  # company, person, event, topic
    name = Column(String(500), nullable=False)
    description = Column(Text)
    
    # For stock symbols if entity is a company
    symbol = Column(String(15), index=True)
    
    # Vector embedding for entity similarity
    embedding = Column(Vector(1536))
    
    # Metadata
    properties = Column(JSON)  # Store additional properties
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    mention_count = Column(Integer, default=1)  # How many times mentioned
    
    __table_args__ = (
        Index('idx_entity_type_symbol', 'entity_type', 'symbol'),
    )


class GraphRelationship(Base):
    """
    Graph database edges representing relationships between entities
    """
    __tablename__ = 'graph_relationships'

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_entity_id = Column(String(255), nullable=False, index=True)
    target_entity_id = Column(String(255), nullable=False, index=True)
    relationship_type = Column(String(100), nullable=False, index=True)  # mentions, affects, competes_with, etc.
    
    # Weight/strength of the relationship
    weight = Column(Float, default=1.0)
    
    # Context of the relationship
    context = Column(Text)
    
    # Source article that established this relationship
    article_id = Column(String(255), ForeignKey('news_articles.article_id'))
    
    # Timestamps
    created_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata
    properties = Column(JSON)
    
    __table_args__ = (
        Index('idx_source_target', 'source_entity_id', 'target_entity_id'),
        Index('idx_relationship_type', 'relationship_type'),
    )


class NewsSummary(Base):
    """
    Aggregated summaries of news analysis for stocks
    Generated and stored by the News_Analyst agent
    """
    __tablename__ = 'news_summaries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(15), nullable=False, index=True)
    summary_date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Time range for this summary
    period = Column(String(50), default='daily')  # daily, weekly, monthly
    
    # Summary content
    summary_text = Column(Text, nullable=False)
    key_events = Column(JSON)  # List of key events
    sentiment_trend = Column(String(50))  # positive, negative, neutral, mixed
    overall_sentiment_score = Column(Float)  # Average sentiment
    
    # Related articles
    article_ids = Column(ARRAY(String))  # List of article IDs used in summary
    article_count = Column(Integer, default=0)
    
    # Metadata
    properties = Column(JSON)
    
    __table_args__ = (
        Index('idx_symbol_period_date', 'symbol', 'period', 'summary_date'),
    )


class EntityMention(Base):
    """
    Links between news articles and entities (many-to-many relationship)
    """
    __tablename__ = 'entity_mentions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(255), ForeignKey('news_articles.article_id'), nullable=False, index=True)
    entity_id = Column(String(255), ForeignKey('graph_entities.entity_id'), nullable=False, index=True)
    
    # How the entity is mentioned
    mention_type = Column(String(50))  # subject, object, context
    mention_context = Column(Text)  # The sentence/paragraph where mentioned
    mention_sentiment = Column(Float)  # Sentiment specifically about this entity in this context
    
    __table_args__ = (
        Index('idx_article_entity', 'article_id', 'entity_id'),
    )
