# NOTE: SQLAlchemy models matching DATABASE.md schema for medical data integrity
from sqlalchemy import Column, String, DateTime, CheckConstraint, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Transfer(Base):
    """Patient transfer records between hospital locations."""
    __tablename__ = "transfers"
    
    transfer_id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), nullable=False, index=True)
    ward_in_time = Column(DateTime, nullable=False)
    ward_out_time = Column(DateTime, nullable=False)
    location = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint('ward_out_time >= ward_in_time', name='chk_transfer_dates'),
        CheckConstraint("transfer_id ~ '^T[A-Z0-9]+$'", name='chk_transfer_id_format'),
        CheckConstraint("patient_id ~ '^P[0-9]+$'", name='chk_patient_id_format'),
        Index('idx_transfers_location_time', 'location', 'ward_in_time', 'ward_out_time'),
        Index('idx_transfers_time_range', 'ward_in_time', 'ward_out_time'),
        Index('idx_transfers_patient_location', 'patient_id', 'location', 'ward_in_time', 'ward_out_time'),
    )

class Microbiology(Base):
    """Infection test results and collection metadata."""
    __tablename__ = "microbiology"
    
    test_id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), nullable=False, index=True)
    collection_date = Column(DateTime, nullable=False)
    infection = Column(String(100), nullable=False)
    result = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        CheckConstraint("result IN ('positive', 'negative')", name='chk_test_result'),
        CheckConstraint("test_id ~ '^M[A-Z0-9]+$'", name='chk_test_id_format'),
        CheckConstraint("patient_id ~ '^P[0-9]+$'", name='chk_patient_id_format'),
        Index('idx_microbiology_infection_result', 'infection', 'result'),
        Index('idx_microbiology_patient_date', 'patient_id', 'collection_date', 'infection'),
    )