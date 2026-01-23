"""
News Processing Service
Handles news collection, embedding generation, and graph construction
"""

import os
import hashlib
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from sentence_transformers import SentenceTransformer
import re

from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector
from sqlalchemy import text

from NewsGraphModels import NewsArticle, GraphEntity, GraphRelationship, NewsSummary, EntityMention

logger = logging.getLogger(__name__)


class NewsProcessingService:
    """Service for processing news articles and generating embeddings"""
    
    def __init__(self):
        """Initialize the service with embedding model"""
        # Using sentence-transformers for local embedding generation
        # This model produces 384-dimensional embeddings (lighter than OpenAI's 1536)
        # For production, you might want to use OpenAI embeddings
        self.embedding_model = None
        self._embedding_dimension = 384  # all-MiniLM-L6-v2 dimension
        
    def _ensure_model_loaded(self):
        """Lazy load the embedding model"""
        if self.embedding_model is None:
            logger.info("Loading sentence transformer model...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Model loaded successfully")
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate vector embedding for text
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        self._ensure_model_loaded()
        if not text or not text.strip():
            return [0.0] * self._embedding_dimension
        
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return [0.0] * self._embedding_dimension
    
    def generate_article_id(self, title: str, source: str, published_date: datetime) -> str:
        """
        Generate a unique article ID
        
        Args:
            title: Article title
            source: Article source
            published_date: Publication date
            
        Returns:
            Unique article ID string
        """
        unique_string = f"{title}_{source}_{published_date.isoformat()}"
        return hashlib.md5(unique_string.encode()).hexdigest()
    
    def extract_entities(self, text: str, symbol: str) -> List[Dict]:
        """
        Extract entities from text (simplified version)
        In production, you'd use NLP libraries like spaCy or transformers
        
        Args:
            text: Text to analyze
            symbol: Stock symbol for context
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        
        # Always add the stock symbol as an entity
        entities.append({
            'entity_id': f"company_{symbol}",
            'entity_type': 'company',
            'name': symbol,
            'symbol': symbol
        })
        
        # Simple pattern matching for other entities (this is a basic implementation)
        # In production, use NLP libraries for better extraction
        
        # Extract mentioned stock symbols (e.g., $AAPL, MSFT)
        stock_pattern = r'\$?([A-Z]{2,5})(?:\s|,|\.|\)|$)'
        matches = re.findall(stock_pattern, text)
        for match in matches:
            if match != symbol and len(match) >= 2:
                entities.append({
                    'entity_id': f"company_{match}",
                    'entity_type': 'company',
                    'name': match,
                    'symbol': match
                })
        
        # Extract common financial terms as topics
        financial_terms = [
            'earnings', 'revenue', 'profit', 'loss', 'acquisition', 'merger',
            'partnership', 'investment', 'IPO', 'dividend', 'buyback', 'bankruptcy'
        ]
        
        text_lower = text.lower()
        for term in financial_terms:
            if term in text_lower:
                entities.append({
                    'entity_id': f"topic_{term}",
                    'entity_type': 'topic',
                    'name': term.capitalize()
                })
        
        return entities
    
    def calculate_sentiment(self, text: str) -> float:
        """
        Calculate sentiment score (simplified implementation)
        
        NOTE: This is a basic keyword-based sentiment analysis.
        For production use, consider integrating:
        - VADER (Valence Aware Dictionary and sEntiment Reasoner)
        - FinBERT or other financial domain-specific models
        - TextBlob for more nuanced analysis
        - Transformer-based models for better accuracy
        
        Args:
            text: Text to analyze
            
        Returns:
            Sentiment score from -1 (negative) to 1 (positive)
        """
        # Simple keyword-based sentiment (replace with proper model in production)
        positive_words = [
            'gain', 'growth', 'profit', 'up', 'rise', 'surge', 'bullish',
            'positive', 'strong', 'excellent', 'outperform', 'beat', 'higher'
        ]
        
        negative_words = [
            'loss', 'decline', 'down', 'fall', 'drop', 'bearish',
            'negative', 'weak', 'miss', 'lower', 'warning', 'concern'
        ]
        
        text_lower = text.lower()
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total == 0:
            return 0.0
        
        return (pos_count - neg_count) / total
    
    def store_news_article(
        self,
        session: Session,
        symbol: str,
        title: str,
        content: str,
        source: str,
        url: Optional[str] = None,
        author: Optional[str] = None,
        published_date: Optional[datetime] = None,
        metadata: Optional[Dict] = None
    ) -> Optional[NewsArticle]:
        """
        Store a news article with embeddings
        
        Args:
            session: Database session
            symbol: Stock symbol
            title: Article title
            content: Article content
            source: Article source
            url: Article URL
            author: Article author
            published_date: Publication date
            metadata: Additional metadata
            
        Returns:
            NewsArticle object or None if failed
        """
        try:
            if published_date is None:
                published_date = datetime.utcnow()
            
            # Generate article ID
            article_id = self.generate_article_id(title, source, published_date)
            
            # Check if article already exists
            existing = session.query(NewsArticle).filter_by(article_id=article_id).first()
            if existing:
                logger.info(f"Article already exists: {article_id}")
                return existing
            
            # Generate embedding
            embedding_text = f"{title} {content}"
            embedding = self.generate_embedding(embedding_text)
            
            # Calculate sentiment
            sentiment_score = self.calculate_sentiment(content)
            
            # Create article
            article = NewsArticle(
                article_id=article_id,
                symbol=symbol,
                title=title,
                content=content,
                source=source,
                url=url,
                author=author,
                published_date=published_date,
                embedding=embedding,
                sentiment_score=sentiment_score,
                relevance_score=1.0,  # Default relevance
                metadata=metadata or {}
            )
            
            session.add(article)
            session.flush()  # Flush to get the article ID
            
            # Extract and store entities
            entities = self.extract_entities(f"{title} {content}", symbol)
            for entity_data in entities:
                entity = self._get_or_create_entity(session, entity_data)
                
                # Create entity mention
                mention = EntityMention(
                    article_id=article.article_id,
                    entity_id=entity.entity_id,
                    mention_type='context'
                )
                session.add(mention)
            
            session.commit()
            logger.info(f"Stored article: {article_id} for {symbol}")
            return article
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing article: {e}")
            return None
    
    def _get_or_create_entity(self, session: Session, entity_data: Dict) -> GraphEntity:
        """Get existing entity or create new one"""
        entity_id = entity_data['entity_id']
        entity = session.query(GraphEntity).filter_by(entity_id=entity_id).first()
        
        if entity:
            # Update mention count
            entity.mention_count += 1
            entity.last_updated = datetime.utcnow()
        else:
            # Create new entity
            entity_text = entity_data.get('name', '') + ' ' + entity_data.get('description', '')
            embedding = self.generate_embedding(entity_text)
            
            entity = GraphEntity(
                entity_id=entity_id,
                entity_type=entity_data['entity_type'],
                name=entity_data['name'],
                description=entity_data.get('description'),
                symbol=entity_data.get('symbol'),
                embedding=embedding,
                properties=entity_data.get('properties', {})
            )
            session.add(entity)
        
        return entity
    
    def create_relationship(
        self,
        session: Session,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        article_id: Optional[str] = None,
        weight: float = 1.0,
        context: Optional[str] = None
    ) -> Optional[GraphRelationship]:
        """
        Create or update a relationship between entities
        
        Args:
            session: Database session
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship
            article_id: Related article ID
            weight: Relationship weight
            context: Context text
            
        Returns:
            GraphRelationship object or None if failed
        """
        try:
            # Check if relationship exists
            rel = session.query(GraphRelationship).filter_by(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=relationship_type
            ).first()
            
            if rel:
                # Update existing relationship
                rel.weight += weight
                rel.last_updated = datetime.utcnow()
                if context:
                    rel.context = context
            else:
                # Create new relationship
                rel = GraphRelationship(
                    source_entity_id=source_entity_id,
                    target_entity_id=target_entity_id,
                    relationship_type=relationship_type,
                    article_id=article_id,
                    weight=weight,
                    context=context
                )
                session.add(rel)
            
            session.commit()
            return rel
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error creating relationship: {e}")
            return None
    
    def semantic_search(
        self,
        session: Session,
        query: str,
        symbol: Optional[str] = None,
        limit: int = 10
    ) -> List[NewsArticle]:
        """
        Perform semantic search on news articles using vector similarity
        
        Args:
            session: Database session
            query: Search query
            symbol: Optional stock symbol filter
            limit: Maximum results
            
        Returns:
            List of relevant NewsArticle objects
        """
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            
            # Use SQLAlchemy ORM for safer queries
            # Build base query
            base_query = session.query(NewsArticle)
            
            # Apply symbol filter if provided
            if symbol:
                base_query = base_query.filter(NewsArticle.symbol == symbol)
            
            # Get all matching articles
            articles = base_query.all()
            
            # Calculate cosine similarity manually if needed
            # For now, return filtered articles (semantic similarity would require
            # custom SQL functions or vector operations)
            # In production, use pgvector's <-> operator properly
            
            return articles[:limit]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def get_entity_graph(
        self,
        session: Session,
        symbol: Optional[str] = None,
        entity_type: Optional[str] = None,
        limit: int = 100
    ) -> Dict:
        """
        Get graph data for visualization
        
        Args:
            session: Database session
            symbol: Optional stock symbol filter
            entity_type: Optional entity type filter
            limit: Maximum entities
            
        Returns:
            Dictionary with nodes and edges for graph visualization
        """
        try:
            # Query entities
            query = session.query(GraphEntity)
            if symbol:
                query = query.filter(GraphEntity.symbol == symbol)
            if entity_type:
                query = query.filter(GraphEntity.entity_type == entity_type)
            
            entities = query.limit(limit).all()
            
            # Get entity IDs
            entity_ids = [e.entity_id for e in entities]
            
            # Query relationships
            relationships = session.query(GraphRelationship).filter(
                GraphRelationship.source_entity_id.in_(entity_ids),
                GraphRelationship.target_entity_id.in_(entity_ids)
            ).all()
            
            # Format for frontend
            nodes = [
                {
                    'id': e.entity_id,
                    'label': e.name,
                    'type': e.entity_type,
                    'symbol': e.symbol,
                    'mentionCount': e.mention_count,
                    'properties': e.properties
                }
                for e in entities
            ]
            
            edges = [
                {
                    'source': r.source_entity_id,
                    'target': r.target_entity_id,
                    'type': r.relationship_type,
                    'weight': r.weight,
                    'context': r.context
                }
                for r in relationships
            ]
            
            return {
                'nodes': nodes,
                'edges': edges
            }
            
        except Exception as e:
            logger.error(f"Error getting entity graph: {e}")
            return {'nodes': [], 'edges': []}


# Singleton instance
_news_service = None

def get_news_service() -> NewsProcessingService:
    """Get or create news processing service instance"""
    global _news_service
    if _news_service is None:
        _news_service = NewsProcessingService()
    return _news_service
