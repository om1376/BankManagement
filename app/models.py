from sqlalchemy import Column, Integer, String, Text, Boolean, DECIMAL, DateTime, ForeignKey, JSON, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Bank(Base):
    __tablename__ = "banks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True, index=True)
    description = Column(Text)
    contact_person = Column(String(255))
    email = Column(String(255))
    phone = Column(String(20))
    address = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    fd_plans = relationship("FDPlan", back_populates="bank", cascade="all, delete-orphan")
    excel_uploads = relationship("ExcelUpload", back_populates="bank", cascade="all, delete-orphan")


class FDPlan(Base):
    __tablename__ = "fd_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_name = Column(String(255), nullable=False)
    minimum_amount = Column(DECIMAL(15, 2), nullable=False)
    maximum_amount = Column(DECIMAL(15, 2))
    tenure_months = Column(Integer, nullable=False)
    base_interest_rate = Column(DECIMAL(5, 4), nullable=False)  # Base interest rate on maturity
    description = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    bank = relationship("Bank", back_populates="fd_plans")
    interest_conditions = relationship("InterestRateCondition", back_populates="fd_plan", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('minimum_amount > 0', name='check_minimum_amount_positive'),
        CheckConstraint('maximum_amount IS NULL OR maximum_amount >= minimum_amount', name='check_maximum_amount_valid'),
        CheckConstraint('tenure_months > 0', name='check_tenure_positive'),
        CheckConstraint('base_interest_rate >= 0', name='check_base_interest_rate_positive'),
    )


class InterestRateCondition(Base):
    __tablename__ = "interest_rate_conditions"
    
    id = Column(Integer, primary_key=True, index=True)
    fd_plan_id = Column(Integer, ForeignKey("fd_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    condition_type = Column(String(50), nullable=False, index=True)  # 'maturity', 'premature'
    min_tenure_months = Column(Integer)  # Minimum tenure for this condition (NULL for maturity)
    max_tenure_months = Column(Integer)  # Maximum tenure for this condition (NULL for maturity)
    interest_rate = Column(DECIMAL(5, 4), nullable=False)
    penalty_rate = Column(DECIMAL(5, 4), default=0.00)  # Penalty rate to be deducted
    penalty_amount = Column(DECIMAL(10, 2), default=0.00)  # Fixed penalty amount
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    fd_plan = relationship("FDPlan", back_populates="interest_conditions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(condition_type = 'maturity' AND min_tenure_months IS NULL AND max_tenure_months IS NULL) OR "
            "(condition_type = 'premature' AND min_tenure_months IS NOT NULL)",
            name='check_valid_tenure_range'
        ),
        CheckConstraint('interest_rate >= 0', name='check_interest_rate_positive'),
        CheckConstraint('penalty_rate >= 0', name='check_penalty_rate_positive'),
        CheckConstraint('penalty_amount >= 0', name='check_penalty_amount_positive'),
    )


class ExcelUpload(Base):
    __tablename__ = "excel_uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    bank_id = Column(Integer, ForeignKey("banks.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_size = Column(Integer)
    upload_status = Column(String(50), default='pending', index=True)  # 'pending', 'processing', 'completed', 'failed'
    total_rows = Column(Integer)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    error_details = Column(Text)
    uploaded_by = Column(String(255))
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    bank = relationship("Bank", back_populates="excel_uploads")
    upload_errors = relationship("UploadError", back_populates="upload", cascade="all, delete-orphan")


class UploadError(Base):
    __tablename__ = "upload_errors"
    
    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("excel_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    row_number = Column(Integer, nullable=False)
    column_name = Column(String(100))
    error_message = Column(Text, nullable=False)
    row_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    upload = relationship("ExcelUpload", back_populates="upload_errors")