"""
Test Script for Vector and Graph Database Implementation
Verifies that all components are working correctly
"""

import os
import sys
# traceback imported at top
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Data_Loader import PostgreSQLConnection
from NewsProcessingService import get_news_service
from NewsGraphModels import NewsArticle, GraphEntity, GraphRelationship, NewsSummary


def test_database_connection():
    """Test database connectivity"""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        db = PostgreSQLConnection.create_connection()
        session = db.get_session()
        
        if session:
            print("✓ Database connection successful")
            session.close()
            db.close()
            return True
        else:
            print("✗ Database connection failed")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_news_processing():
    """Test news processing service"""
    print("\n" + "=" * 60)
    print("Testing News Processing Service")
    print("=" * 60)
    
    try:
        news_service = get_news_service()
        
        # Test embedding generation
        test_text = "Apple announces new iPhone with advanced AI features"
        embedding = news_service.generate_embedding(test_text)
        
        if len(embedding) == 384:  # Check dimension
            print(f"✓ Embedding generation successful (dimension: {len(embedding)})")
        else:
            print(f"✗ Unexpected embedding dimension: {len(embedding)}")
            return False
        
        # Test sentiment calculation
        sentiment = news_service.calculate_sentiment(test_text)
        print(f"✓ Sentiment calculation successful (score: {sentiment:.2f})")
        
        # Test entity extraction
        entities = news_service.extract_entities(test_text, "AAPL")
        print(f"✓ Entity extraction successful (found {len(entities)} entities)")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        # traceback imported at top
        traceback.print_exc()
        return False


def test_news_storage():
    """Test storing news article"""
    print("\n" + "=" * 60)
    print("Testing News Article Storage")
    print("=" * 60)
    
    try:
        db = PostgreSQLConnection.create_connection()
        session = db.get_session()
        news_service = get_news_service()
        
        # Create test article
        article = news_service.store_news_article(
            session=session,
            symbol="AAPL",
            title="Test Article: Apple Announces Innovation",
            content="Apple Inc. announced today a revolutionary new feature that will change the industry.",
            source="Test",
            published_date=datetime.utcnow()
        )
        
        if article:
            print(f"✓ Article stored successfully (ID: {article.article_id})")
            print(f"  - Sentiment: {article.sentiment_score:.2f}")
            print(f"  - Embedding dimension: {len(article.embedding) if article.embedding else 0}")
            
            # Check if entities were created
            entities_count = session.query(GraphEntity).filter(
                GraphEntity.symbol == "AAPL"
            ).count()
            print(f"✓ Created/updated {entities_count} entities")
            
            session.close()
            db.close()
            return True
        else:
            print("✗ Failed to store article")
            session.close()
            db.close()
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        # traceback imported at top
        traceback.print_exc()
        return False


def test_graph_retrieval():
    """Test graph data retrieval"""
    print("\n" + "=" * 60)
    print("Testing Graph Data Retrieval")
    print("=" * 60)
    
    try:
        db = PostgreSQLConnection.create_connection()
        session = db.get_session()
        news_service = get_news_service()
        
        # Get graph data
        graph_data = news_service.get_entity_graph(
            session=session,
            symbol="AAPL",
            limit=50
        )
        
        nodes_count = len(graph_data['nodes'])
        edges_count = len(graph_data['edges'])
        
        print(f"✓ Retrieved graph data successfully")
        print(f"  - Nodes: {nodes_count}")
        print(f"  - Edges: {edges_count}")
        
        if nodes_count > 0:
            print(f"  - Sample node: {graph_data['nodes'][0]['label']}")
        
        session.close()
        db.close()
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        # traceback imported at top
        traceback.print_exc()
        return False


def test_database_tables():
    """Test that all required tables exist"""
    print("\n" + "=" * 60)
    print("Testing Database Tables")
    print("=" * 60)
    
    try:
        db = PostgreSQLConnection.create_connection()
        tables = db.get_tables()
        
        required_tables = [
            'news_articles',
            'graph_entities',
            'graph_relationships',
            'news_summaries',
            'entity_mentions'
        ]
        
        all_exist = True
        for table in required_tables:
            if table in tables:
                print(f"✓ {table}")
            else:
                print(f"✗ {table} - NOT FOUND")
                all_exist = False
        
        db.close()
        return all_exist
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_semantic_search():
    """Test semantic search functionality"""
    print("\n" + "=" * 60)
    print("Testing Semantic Search")
    print("=" * 60)
    
    try:
        db = PostgreSQLConnection.create_connection()
        session = db.get_session()
        news_service = get_news_service()
        
        # Check if we have any articles
        article_count = session.query(NewsArticle).count()
        
        if article_count == 0:
            print("⚠ No articles in database, skipping semantic search test")
            session.close()
            db.close()
            return True
        
        # Perform semantic search
        results = news_service.semantic_search(
            session=session,
            query="innovation and technology",
            limit=5
        )
        
        print(f"✓ Semantic search successful")
        print(f"  - Found {len(results)} relevant articles")
        
        if results:
            print(f"  - Top result: {results[0].title}")
        
        session.close()
        db.close()
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        # traceback imported at top
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("*" * 60)
    print("Vector & Graph Database Test Suite")
    print("*" * 60)
    print()
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Database Tables", test_database_tables),
        ("News Processing", test_news_processing),
        ("News Storage", test_news_storage),
        ("Graph Retrieval", test_graph_retrieval),
        ("Semantic Search", test_semantic_search),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
