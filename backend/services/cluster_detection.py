import pandas as pd
from datetime import timedelta, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models import Transfer, Microbiology
from typing import List, Dict, Any
import io

def parse_and_store_csv(db: Session, transfers_content: bytes, microbiology_content: bytes) -> Dict[str, Any]:
    """
    Parse CSV files and store data in PostgreSQL database.
    NOTE: Replaces direct CSV processing with database persistence for medical data integrity
    """
    try:
        # Parse CSV content using pandas
        transfers_df = pd.read_csv(io.BytesIO(transfers_content))
        microbiology_df = pd.read_csv(io.BytesIO(microbiology_content))
        
        # Convert date columns to datetime objects
        transfers_df['ward_in_time'] = pd.to_datetime(transfers_df['ward_in_time'])
        transfers_df['ward_out_time'] = pd.to_datetime(transfers_df['ward_out_time'])
        microbiology_df['collection_date'] = pd.to_datetime(microbiology_df['collection_date'])
        
        # Clear existing data (for development - in production, consider upsert logic)
        # FIXME - Could open up a MITM attack (High I/O overhead)
        db.query(Transfer).delete()
        db.query(Microbiology).delete()
        
        # Store transfers data
        transfers_count = 0
        for _, row in transfers_df.iterrows():
            transfer = Transfer(
                transfer_id=str(row['transfer_id']),
                patient_id=str(row['patient_id']),
                ward_in_time=row['ward_in_time'].to_pydatetime(),
                ward_out_time=row['ward_out_time'].to_pydatetime(),
                location=str(row['location'])
            )
            db.add(transfer)
            transfers_count += 1
        
        # Store microbiology data
        microbiology_count = 0
        for _, row in microbiology_df.iterrows():
            microbiology = Microbiology(
                test_id=str(row['test_id']),
                patient_id=str(row['patient_id']),
                collection_date=row['collection_date'].to_pydatetime(),
                infection=str(row['infection']),
                result=str(row['result'])
            )
            db.add(microbiology)
            microbiology_count += 1
        
        db.commit()
        
        return {
            "transfers_imported": transfers_count,
            "microbiology_imported": microbiology_count,
            "status": "success"
        }
        
    except Exception as e:
        db.rollback()
        raise Exception(f"Error parsing and storing CSV data: {str(e)}")

def find_clusters_from_db(db: Session, time_window: int = 14, location_overlap: bool = True) -> Dict[str, Any]:
    """
    Identifies infection clusters using database queries for optimal performance.
    NOTE: Database-optimized cluster detection with temporal and spatial analysis
    """
    try:
        # Get all positive microbiology tests
        positive_tests = db.query(Microbiology).filter(Microbiology.result == 'positive').all()

        # Group positive tests by infection type
        tests_by_infection = {}
        for test in positive_tests:
            if test.infection not in tests_by_infection:
                tests_by_infection[test.infection] = []
            tests_by_infection[test.infection].append(test)

        # Pre-fetch all transfers for patients with positive tests for efficiency
        positive_patient_ids = [pt.patient_id for pt in positive_tests]
        all_transfers = db.query(Transfer).filter(Transfer.patient_id.in_(positive_patient_ids)).all()

        patient_transfers = {}
        for t in all_transfers:
            if t.patient_id not in patient_transfers:
                patient_transfers[t.patient_id] = []
            patient_transfers[t.patient_id].append(t)

        clusters = {}

        for infection, tests in tests_by_infection.items():
            if infection not in clusters:
                clusters[infection] = []

            patient_pairs = set()

            for i in range(len(tests)):
                for j in range(i + 1, len(tests)):
                    test1 = tests[i]
                    test2 = tests[j]

                    if test1.patient_id == test2.patient_id:
                        continue

                    # Ensure consistent pair ordering to avoid duplicates
                    pair = tuple(sorted((test1.patient_id, test2.patient_id)))
                    if pair in patient_pairs:
                        continue

                    p1_transfers = patient_transfers.get(test1.patient_id, [])
                    p2_transfers = patient_transfers.get(test2.patient_id, [])

                    if _check_temporal_spatial_link(test1, test2, p1_transfers, p2_transfers, time_window, location_overlap):
                        patient_pairs.add(pair)

                        # Add to existing cluster or create a new one
                        found_cluster = False
                        for cluster_info in clusters[infection]:
                            if test1.patient_id in cluster_info['patients'] or test2.patient_id in cluster_info['patients']:
                                cluster_info['patients'].update([test1.patient_id, test2.patient_id])
                                found_cluster = True
                                break

                        if not found_cluster:
                            clusters[infection].append({
                                'patients': {test1.patient_id, test2.patient_id},
                                'start_date': min(test1.collection_date, test2.collection_date).date().isoformat(),
                                'end_date': max(test1.collection_date, test2.collection_date).date().isoformat()
                            })

        # Convert sets to lists for JSON serialization
        for infection in clusters:
            for cluster_info in clusters[infection]:
                cluster_info['patients'] = sorted(list(cluster_info['patients']))

        return clusters
    except Exception as e:
        raise Exception(f"Error detecting clusters: {str(e)}")

def _check_temporal_spatial_link(test1, test2, p1_transfers, p2_transfers, time_window, location_overlap):
    """Check for a temporal and spatial link between two patients."""
    
    # Check time window between positive tests
    time_diff = abs((test1.collection_date - test2.collection_date).days)
    if time_diff > time_window:
        return False

    if not location_overlap:
        return True

    # Check for overlapping stays in the same location
    for t1 in p1_transfers:
        for t2 in p2_transfers:
            if t1.location == t2.location:
                overlap_start = max(t1.ward_in_time, t2.ward_in_time)
                overlap_end = min(t1.ward_out_time, t2.ward_out_time)
                if overlap_start <= overlap_end:
                    return True
    
    return False

def get_cluster_statistics(db: Session) -> Dict[str, Any]:
    """
    Get statistics about the stored data and detected clusters.
    NOTE: Analytics endpoint for clinical dashboard
    """
    try:
        total_transfers = db.query(Transfer).count()
        total_tests = db.query(Microbiology).count()
        positive_tests = db.query(Microbiology).filter(
            Microbiology.result == 'positive'
        ).count()
        unique_patients = db.query(Transfer.patient_id).distinct().count()
        unique_locations = db.query(Transfer.location).distinct().count()
        
        clusters = find_clusters_from_db(db)
        total_clusters = sum(len(infection_clusters) for infection_clusters in clusters.values())
        
        return {
            "total_transfers": total_transfers,
            "total_tests": total_tests,
            "positive_tests": positive_tests,
            "unique_patients": unique_patients,
            "unique_locations": unique_locations,
            "total_clusters": total_clusters,
            "clusters_by_infection": {k: len(v) for k, v in clusters.items()}
        }
        
    except Exception as e:
        raise Exception(f"Error getting statistics: {str(e)}")
