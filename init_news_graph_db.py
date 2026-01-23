"""
Initialize database with News and Graph models
Run this script to create the new tables for Vector and Graph database
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from NewsGraphModels import Base as NewsGraphBase
from Data_Loader import Base as DataLoaderBase


def init_news_graph_database(
    host: str = None,
    port: int = None,
    database: str = None,
    user: str = None,
    password: str = None
):
    """
    Initialize database with News and Graph models
    
    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user
        password: Database password
    """
    # Use environment variables or defaults
    host = host or os.getenv("DB_HOST", "localhost")
    port = port or int(os.getenv("DB_PORT", "5432"))
    database = database or os.getenv("DB_NAME", "postgres")
    user = user or os.getenv("DB_USER", "postgres")
    password = password or os.getenv("DB_PASSWORD", "postgres")
    
    # Create database URL
    database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        # Create engine
        engine = create_engine(database_url, echo=True)
        
        # Test connection
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print(f"✓ Connected to database: {database}")
            
            # Enable pgvector extension
            try:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                connection.commit()
                print("✓ pgvector extension enabled")
            except Exception as e:
                print(f"⚠ Warning: Could not enable pgvector extension: {e}")
                print("  Make sure PostgreSQL has the pgvector extension installed")
                print("  Installation: https://github.com/pgvector/pgvector")
        
        # Create all tables from both Base classes
        print("\n📊 Creating tables from Data_Loader models...")
        DataLoaderBase.metadata.create_all(engine)
        
        print("\n📊 Creating tables from NewsGraph models...")
        NewsGraphBase.metadata.create_all(engine)
        
        print("\n✓ All tables created successfully!")
        
        # Show created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n📋 Total tables in database: {len(tables)}")
        for i, table in enumerate(sorted(tables), 1):
            print(f"  {i}. {table}")
        
        # Check for news and graph tables
        news_graph_tables = [
            'news_articles',
            'graph_entities', 
            'graph_relationships',
            'news_summaries',
            'entity_mentions'
        ]
        
        print("\n✓ News and Graph Database tables:")
        for table in news_graph_tables:
            status = "✓" if table in tables else "✗"
            print(f"  {status} {table}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("News & Graph Database Initialization")
    print("=" * 60)
    print()
    
    success = init_news_graph_database()
    
    if success:
        print("\n" + "=" * 60)
        print("✓ Database initialization completed successfully!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("✗ Database initialization failed!")
        print("=" * 60)
        sys.exit(1)
