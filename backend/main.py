from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
from database import get_db, create_tables, test_connection
from services.cluster_detection import parse_and_store_csv, find_clusters_from_db, get_cluster_statistics
from models import Transfer, Microbiology

# NOTE: Initialize FastAPI with PostgreSQL backend for medical data persistence
app = FastAPI(
    title="Infection Cluster Detection API",
    description="Medical data processing system for hospital infection cluster detection",
    version="1.0.0"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables and verify connection on startup."""
    if not test_connection():
        raise HTTPException(status_code=500, detail="Database connection failed")
    create_tables()

# NOTE: CORS configuration for Angular frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: Remove file-based storage, using PostgreSQL for data persistence
# DATA_DIR removed - using database storage per CLAUDE.md requirements

@app.post("/upload/")
async def upload_files(
    files: List[UploadFile] = File(...), 
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Upload and process CSV files, storing data in PostgreSQL database.
    NOTE: Medical data ingestion with ACID compliance for clinical integrity
    """
    if len(files) != 2:
        raise HTTPException(
            status_code=400, 
            detail="Please upload exactly two files: transfers.csv and microbiology.csv"
        )
    
    # Validate file types
    expected_files = {"transfers.csv", "microbiology.csv"}
    uploaded_files = {file.filename for file in files}
    
    if uploaded_files != expected_files:
        raise HTTPException(
            status_code=400,
            detail=f"Expected files: {expected_files}, got: {uploaded_files}"
        )
    
    try:
        # Read file contents
        transfers_content = None
        microbiology_content = None
        
        for file in files:
            content = await file.read()
            if file.filename == "transfers.csv":
                transfers_content = content
            elif file.filename == "microbiology.csv":
                microbiology_content = content
        
        # Parse and store in database
        result = parse_and_store_csv(db, transfers_content, microbiology_content)
        
        return {
            "message": "Files uploaded and processed successfully",
            "details": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing uploaded files: {str(e)}"
        )


@app.get("/clusters/")
async def get_clusters(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Detect infection clusters from database using optimized queries.
    NOTE: Database-driven cluster detection for clinical analysis
    """
    try:
        # Check if data exists in database
        transfer_count = db.query(Transfer).count()
        microbiology_count = db.query(Microbiology).count()
        
        if transfer_count == 0 or microbiology_count == 0:
            raise HTTPException(
                status_code=400, 
                detail="No data found. Please upload the CSV files first."
            )
        
        # Detect clusters using database queries
        clusters = find_clusters_from_db(db)
        
        # Transform to match frontend expectations (simplified format)
        simplified_clusters = {}
        for infection, cluster_info_list in clusters.items():
            simplified_clusters[infection] = [cluster['patients'] for cluster in cluster_info_list]
        
        return simplified_clusters
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error detecting clusters: {str(e)}"
        )


@app.get("/statistics/")
async def get_statistics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get comprehensive statistics about the stored data and detected clusters.
    NOTE: Analytics endpoint for clinical dashboard insights
    """
    try:
        stats = get_cluster_statistics(db)
        return stats
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting statistics: {str(e)}"
        )


@app.get("/health/")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint for monitoring database connectivity.
    NOTE: System health monitoring for medical application reliability
    """
    db_status = "healthy" if test_connection() else "unhealthy"
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "service": "infection_cluster_detection"
    }


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "Infection Cluster Detection API",
        "version": "1.0.0",
        "endpoints": "/docs for API documentation"
    }