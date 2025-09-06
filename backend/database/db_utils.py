"""
Database utilities for infection cluster detection system.
Handles PostgreSQL connection, CSV data loading, and common database operations.
"""

import os
import asyncio
import pandas as pd
import asyncpg
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

# NOTE: Database utilities optimized for bulk CSV loading and cluster queries

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database connections and operations for infection cluster detection."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "infection_cluster_db",
        username: str = "postgres",
        password: str = "password",
        schema: str = "infection_cluster"
    ):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.schema = schema
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """Establish database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.username,
                password=self.password,
                command_timeout=60,
                server_settings={
                    'search_path': f'{self.schema},public'
                },
                min_size=2,
                max_size=10
            )
            logger.info(f"Connected to PostgreSQL database: {self.database}")
            
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection closed")
    
    async def execute_query(self, query: str, *args) -> List[Dict]:
        """Execute a query and return results."""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as connection:
            try:
                rows = await connection.fetch(query, *args)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                raise
    
    async def execute_command(self, command: str, *args) -> str:
        """Execute a command (INSERT, UPDATE, DELETE) and return status."""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as connection:
            try:
                result = await connection.execute(command, *args)
                logger.info(f"Command executed: {result}")
                return result
            except Exception as e:
                logger.error(f"Command execution failed: {e}")
                raise

class CSVDataLoader:
    """Handles loading CSV data into PostgreSQL tables."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def load_transfers_csv(self, csv_path: str) -> int:
        """
        Load transfers.csv data into the transfers table.
        Returns number of records inserted.
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            logger.info(f"Loading {len(df)} transfer records from {csv_path}")
            
            # Validate required columns
            required_cols = ['transfer_id', 'patient_id', 'ward_in_time', 'ward_out_time', 'location']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Data preprocessing
            df['ward_in_time'] = pd.to_datetime(df['ward_in_time']).dt.date
            df['ward_out_time'] = pd.to_datetime(df['ward_out_time'], errors='coerce').dt.date
            
            # Clean string fields
            df['transfer_id'] = df['transfer_id'].astype(str).str.strip()
            df['patient_id'] = df['patient_id'].astype(str).str.strip()
            df['location'] = df['location'].astype(str).str.strip()
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['transfer_id'])
            
            # Insert patient IDs first (to satisfy foreign key constraint)
            unique_patients = df['patient_id'].unique()
            await self._insert_patients(unique_patients)
            
            # Insert transfers
            records_inserted = 0
            async with self.db_manager.pool.acquire() as connection:
                async with connection.transaction():
                    for _, row in df.iterrows():
                        try:
                            await connection.execute("""
                                INSERT INTO transfers (transfer_id, patient_id, ward_in_time, ward_out_time, location)
                                VALUES ($1, $2, $3, $4, $5)
                                ON CONFLICT (transfer_id) DO NOTHING
                            """, 
                            row['transfer_id'],
                            row['patient_id'],
                            row['ward_in_time'],
                            row['ward_out_time'] if pd.notna(row['ward_out_time']) else None,
                            row['location']
                            )
                            records_inserted += 1
                        except Exception as e:
                            logger.warning(f"Skipped transfer {row['transfer_id']}: {e}")
            
            logger.info(f"Successfully loaded {records_inserted} transfer records")
            return records_inserted
            
        except Exception as e:
            logger.error(f"Failed to load transfers CSV: {e}")
            raise
    
    async def load_microbiology_csv(self, csv_path: str) -> int:
        """
        Load microbiology.csv data into the microbiology table.
        Returns number of records inserted.
        """
        try:
            # Read CSV file
            df = pd.read_csv(csv_path)
            logger.info(f"Loading {len(df)} microbiology records from {csv_path}")
            
            # Validate required columns
            required_cols = ['test_id', 'patient_id', 'collection_date', 'infection', 'result']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # Data preprocessing
            df['collection_date'] = pd.to_datetime(df['collection_date']).dt.date
            
            # Clean string fields
            df['test_id'] = df['test_id'].astype(str).str.strip()
            df['patient_id'] = df['patient_id'].astype(str).str.strip()
            df['infection'] = df['infection'].astype(str).str.strip()
            df['result'] = df['result'].astype(str).str.strip().str.lower()
            
            # Validate result values
            valid_results = ['positive', 'negative']
            invalid_results = df[~df['result'].isin(valid_results)]
            if len(invalid_results) > 0:
                logger.warning(f"Found {len(invalid_results)} records with invalid results, skipping...")
                df = df[df['result'].isin(valid_results)]
            
            # Remove duplicates
            df = df.drop_duplicates(subset=['test_id'])
            
            # Insert patient IDs first (to satisfy foreign key constraint)
            unique_patients = df['patient_id'].unique()
            await self._insert_patients(unique_patients)
            
            # Insert microbiology tests
            records_inserted = 0
            async with self.db_manager.pool.acquire() as connection:
                async with connection.transaction():
                    for _, row in df.iterrows():
                        try:
                            await connection.execute("""
                                INSERT INTO microbiology (test_id, patient_id, collection_date, infection, result)
                                VALUES ($1, $2, $3, $4, $5)
                                ON CONFLICT (test_id) DO NOTHING
                            """,
                            row['test_id'],
                            row['patient_id'],
                            row['collection_date'],
                            row['infection'],
                            row['result']
                            )
                            records_inserted += 1
                        except Exception as e:
                            logger.warning(f"Skipped test {row['test_id']}: {e}")
            
            logger.info(f"Successfully loaded {records_inserted} microbiology records")
            
            # Refresh materialized view after loading data
            await self._refresh_materialized_view()
            
            return records_inserted
            
        except Exception as e:
            logger.error(f"Failed to load microbiology CSV: {e}")
            raise
    
    async def _insert_patients(self, patient_ids: List[str]) -> None:
        """Insert unique patient IDs into patients table."""
        async with self.db_manager.pool.acquire() as connection:
            async with connection.transaction():
                for patient_id in patient_ids:
                    await connection.execute("""
                        INSERT INTO patients (patient_id) VALUES ($1)
                        ON CONFLICT (patient_id) DO NOTHING
                    """, patient_id)
    
    async def _refresh_materialized_view(self) -> None:
        """Refresh the materialized view for cluster detection."""
        try:
            await self.db_manager.execute_command("SELECT refresh_patient_infection_timeline()")
            logger.info("Materialized view refreshed successfully")
        except Exception as e:
            logger.warning(f"Failed to refresh materialized view: {e}")

class ClusterQueryBuilder:
    """Builds optimized queries for infection cluster detection."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    async def get_positive_cases_by_infection(
        self, 
        infection_type: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """Get all positive cases with location and timing information."""
        
        query = """
        SELECT 
            pit.patient_id,
            pit.infection,
            pit.infection_date,
            pit.location,
            pit.ward_in_time,
            pit.ward_out_time,
            pit.infection_during_stay
        FROM patient_infection_timeline pit
        WHERE 1=1
        """
        
        params = []
        param_idx = 1
        
        if infection_type:
            query += f" AND pit.infection = ${param_idx}"
            params.append(infection_type)
            param_idx += 1
        
        if start_date:
            query += f" AND pit.infection_date >= ${param_idx}"
            params.append(start_date)
            param_idx += 1
        
        if end_date:
            query += f" AND pit.infection_date <= ${param_idx}"
            params.append(end_date)
            param_idx += 1
        
        query += " ORDER BY pit.infection_date, pit.infection, pit.location"
        
        return await self.db_manager.execute_query(query, *params)
    
    async def find_spatial_temporal_clusters(
        self,
        infection_type: str,
        contact_window_days: int = 14,
        min_cluster_size: int = 2
    ) -> List[Dict]:
        """
        Find spatial-temporal clusters based on overlapping stays and infection timing.
        
        Args:
            infection_type: Type of infection to analyze
            contact_window_days: Days around infection date to consider for contact
            min_cluster_size: Minimum number of patients for a cluster
        """
        
        query = """
        WITH infection_contacts AS (
            SELECT 
                pit1.patient_id as patient_1,
                pit2.patient_id as patient_2,
                pit1.infection_date as infection_date_1,
                pit2.infection_date as infection_date_2,
                pit1.location,
                CASE 
                    WHEN pit1.ward_in_time <= pit2.ward_out_time 
                    AND pit2.ward_in_time <= pit1.ward_out_time
                    THEN true 
                    ELSE false 
                END as location_overlap,
                ABS(pit1.infection_date - pit2.infection_date) as days_between_infections
            FROM patient_infection_timeline pit1
            JOIN patient_infection_timeline pit2 
                ON pit1.location = pit2.location 
                AND pit1.patient_id != pit2.patient_id
                AND pit1.infection = pit2.infection
            WHERE pit1.infection = $1
            AND pit1.infection_during_stay = true
            AND pit2.infection_during_stay = true
        ),
        potential_clusters AS (
            SELECT 
                location,
                COUNT(DISTINCT patient_1) + COUNT(DISTINCT patient_2) as cluster_size,
                MIN(LEAST(infection_date_1, infection_date_2)) as cluster_start,
                MAX(GREATEST(infection_date_1, infection_date_2)) as cluster_end,
                AVG(days_between_infections) as avg_days_between
            FROM infection_contacts
            WHERE location_overlap = true
            AND days_between_infections <= $2
            GROUP BY location
            HAVING COUNT(DISTINCT patient_1) + COUNT(DISTINCT patient_2) >= $3
        )
        SELECT 
            location,
            cluster_size,
            cluster_start,
            cluster_end,
            cluster_end - cluster_start + 1 as cluster_duration_days,
            ROUND(avg_days_between, 1) as avg_days_between_infections
        FROM potential_clusters
        ORDER BY cluster_size DESC, cluster_start DESC
        """
        
        return await self.db_manager.execute_query(
            query, 
            infection_type, 
            contact_window_days, 
            min_cluster_size
        )
    
    async def get_location_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """Get infection statistics by location."""
        
        query = """
        SELECT * FROM get_infection_stats_by_location($1, $2, $3)
        """
        
        return await self.db_manager.execute_query(
            query,
            None,  # infection_type (all infections)
            start_date,
            end_date
        )

# NOTE: Factory function for easy initialization
async def create_database_manager() -> DatabaseManager:
    """Create and initialize database manager with environment variables."""
    db_manager = DatabaseManager(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'infection_cluster_db'),
        username=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password'),
        schema=os.getenv('DB_SCHEMA', 'infection_cluster')
    )
    await db_manager.connect()
    return db_manager

# NOTE: Example usage and testing functions
async def main():
    """Example usage of database utilities."""
    try:
        # Initialize database manager
        db_manager = await create_database_manager()
        
        # Initialize CSV loader
        csv_loader = CSVDataLoader(db_manager)
        
        # Load CSV files (adjust paths as needed)
        data_dir = Path("../../data")
        
        if (data_dir / "transfers.csv").exists():
            await csv_loader.load_transfers_csv(str(data_dir / "transfers.csv"))
        
        if (data_dir / "microbiology.csv").exists():
            await csv_loader.load_microbiology_csv(str(data_dir / "microbiology.csv"))
        
        # Example cluster detection queries
        query_builder = ClusterQueryBuilder(db_manager)
        
        # Find CRE clusters
        clusters = await query_builder.find_spatial_temporal_clusters(
            infection_type="CRE",
            contact_window_days=14,
            min_cluster_size=2
        )
        
        print("Detected CRE clusters:")
        for cluster in clusters:
            print(f"  Location: {cluster['location']}")
            print(f"  Size: {cluster['cluster_size']} patients")
            print(f"  Duration: {cluster['cluster_duration_days']} days")
            print()
        
        # Get location statistics
        stats = await query_builder.get_location_statistics()
        print("Location infection statistics:")
        for stat in stats:
            print(f"  {stat['location']}: {stat['positive_cases']}/{stat['total_patients']} ({stat['infection_rate']}%)")
        
        await db_manager.disconnect()
        
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())

# NOTE: Database utilities provide complete data pipeline from CSV to cluster detection
# NOTE: Async design supports high-performance concurrent operations
# NOTE: Built-in error handling and logging for production medical environment