# NOTE: Database initialization and table creation for medical data system
from sqlalchemy import create_engine, text
from models import Base
from database import DATABASE_URL, engine
import os

def setup_database() -> bool:
    """Initialize database connection and create tables if they don't exist."""
    try:
        print("Testing database connection...")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"Connected to PostgreSQL: {version[:50]}...")
        
        print("Creating database tables...")
        
        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        
        print("Database setup completed successfully")
        print("Available tables: transfers, microbiology")
        
        return True
        
    except Exception as e:
        print(f"Database setup failed: {e}")
        print("Make sure PostgreSQL is running and credentials are correct")
        print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'localhost:5432/infection_clusters'}")
        return False

def check_tables() -> bool:
    """Check if required tables exist."""
    try:
        with engine.connect() as conn:
            # Check if transfers table exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'transfers')"
            ))
            transfers_exists = result.fetchone()[0]
            
            # Check if microbiology table exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'microbiology')"
            ))
            microbiology_exists = result.fetchone()[0]
            
            return transfers_exists and microbiology_exists
    except Exception:
        return False

if __name__ == "__main__":
    success = setup_database()
    if success:
        print("\nReady to start the application!")
    else:
        print("\nPlease fix database issues before starting the application")
        exit(1)