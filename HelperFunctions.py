import os
from typing import Any, Optional

def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Missing environment variable: {name}")
    return val

def get_database_url() -> str:
    DATABASE_URL = "localhost:5432/Stocks_Database"
    return DATABASE_URL

def to_float(value: Any) -> Optional[float]:
    """Coerce numpy/pandas scalars/strings into a real Python float."""
    if value is None:
        return None
    try:
        # numpy/pandas scalar -> python scalar
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except Exception:
        return None

# Connect to the database using the URL from environment variable
def connect_to_database():
    db_url = get_database_url()
    # Here you would add the logic to connect to the database using db_url
    print(f"Connecting to database at {db_url}")
    # Example: Using psycopg2 to connect to PostgreSQL
    # import psycopg2
    # conn = psycopg2.connect(db_url)
    # return conn


