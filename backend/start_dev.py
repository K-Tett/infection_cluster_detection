#!/usr/bin/env python3
"""
Development startup script for infection cluster detection backend.
NOTE: Local development helper with database initialization
"""
import os
import sys
import subprocess
from setup_db import setup_database

def main():
    """Start development server with database setup."""
    print("Infection Cluster Detection - Development Server")
    print("=" * 50)
    
    # Set development environment
    os.environ["ENVIRONMENT"] = "development"
    
    # Setup database if needed
    print("Checking database setup...")
    if not setup_database():
        print("Database setup failed. Please check PostgreSQL connection.")
        sys.exit(1)
    
    print("\nStarting FastAPI development server...")
    print("Server will be available at: http://127.0.0.1:8000")
    print("API documentation: http://127.0.0.1:8000/docs")
    print("Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        # Start FastAPI server with hot reload
        subprocess.run([
            "uvicorn", 
            "main:app", 
            "--host", "127.0.0.1", 
            "--port", "8000", 
            "--reload",
            "--log-level", "info"
        ], cwd="backend")
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except FileNotFoundError:
        print("\nuvicorn not found. Please install requirements:")
        print("pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()