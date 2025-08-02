from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from decimal import Decimal
import json

from app.models import Bank, FDPlan, InterestRateCondition, ExcelUpload, UploadError
from app.schemas import (
    BankCreate, BankUpdate, BankFilter,
    FDPlanCreate, FDPlanUpdate, FDPlanFilter,
    InterestRateConditionCreate, InterestRateConditionUpdate,
    ExcelUploadCreate
)


# Bank CRUD Operations
class BankCRUD:
    @staticmethod
    def create(db: Session, bank_data: BankCreate) -> Bank:
        """Create a new bank"""
        db_bank = Bank(**bank_data.dict())
        db.add(db_bank)
        db.commit()
        db.refresh(db_bank)
        return db_bank
    
    @staticmethod
    def get(db: Session, bank_id: int) -> Optional[Bank]:
        """Get bank by ID"""
        return db.query(Bank).filter(Bank.id == bank_id).first()
    
    @staticmethod
    def get_by_code(db: Session, bank_code: str) -> Optional[Bank]:
        """Get bank by code"""
        return db.query(Bank).filter(Bank.code == bank_code).first()
    
    @staticmethod
    def get_by_name(db: Session, bank_name: str) -> Optional[Bank]:
        """Get bank by name"""
        return db.query(Bank).filter(Bank.name == bank_name).first()
    
    @staticmethod
    def get_list(db: Session, filters: BankFilter) -> tuple[List[Bank], int]:
        """Get filtered list of banks with pagination"""
        query = db.query(Bank)
        
        # Apply filters
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                or_(
                    Bank.name.ilike(search_term),
                    Bank.code.ilike(search_term),
                    Bank.contact_person.ilike(search_term)
                )
            )
        
        if filters.is_active is not None:
            query = query.filter(Bank.is_active == filters.is_active)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        banks = query.offset(offset).limit(filters.per_page).all()
        
        return banks, total
    
    @staticmethod
    def update(db: Session, bank_id: int, bank_update: BankUpdate) -> Optional[Bank]:
        """Update bank"""
        bank = db.query(Bank).filter(Bank.id == bank_id).first()
        if not bank:
            return None
        
        update_data = bank_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(bank, field, value)
        
        db.commit()
        db.refresh(bank)
        return bank
    
    @staticmethod
    def delete(db: Session, bank_id: int) -> bool:
        """Delete bank"""
        bank = db.query(Bank).filter(Bank.id == bank_id).first()
        if not bank:
            return False
        
        db.delete(bank)
        db.commit()
        return True
    
    @staticmethod
    def toggle_active(db: Session, bank_id: int) -> Optional[Bank]:
        """Toggle bank active status"""
        bank = db.query(Bank).filter(Bank.id == bank_id).first()
        if not bank:
            return None
        
        bank.is_active = not bank.is_active
        db.commit()
        db.refresh(bank)
        return bank


# FD Plan CRUD Operations
class FDPlanCRUD:
    @staticmethod
    def create(db: Session, fd_plan_data: FDPlanCreate) -> FDPlan:
        """Create a new FD plan with interest conditions"""
        # Extract interest conditions
        interest_conditions_data = fd_plan_data.interest_conditions
        fd_plan_dict = fd_plan_data.dict(exclude={"interest_conditions"})
        
        # Create FD plan
        db_fd_plan = FDPlan(**fd_plan_dict)
        db.add(db_fd_plan)
        db.flush()  # Flush to get ID
        
        # Create interest conditions
        for condition_data in interest_conditions_data:
            condition_dict = condition_data.dict()
            condition_dict["fd_plan_id"] = db_fd_plan.id
            db_condition = InterestRateCondition(**condition_dict)
            db.add(db_condition)
        
        db.commit()
        db.refresh(db_fd_plan)
        return db_fd_plan
    
    @staticmethod
    def get(db: Session, fd_plan_id: int) -> Optional[FDPlan]:
        """Get FD plan by ID with related data"""
        return db.query(FDPlan).options(
            joinedload(FDPlan.bank),
            joinedload(FDPlan.interest_conditions)
        ).filter(FDPlan.id == fd_plan_id).first()
    
    @staticmethod
    def get_list(db: Session, filters: FDPlanFilter) -> tuple[List[FDPlan], int]:
        """Get filtered list of FD plans with pagination"""
        query = db.query(FDPlan).options(
            joinedload(FDPlan.bank),
            joinedload(FDPlan.interest_conditions)
        )
        
        # Apply filters
        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.join(Bank).filter(
                or_(
                    FDPlan.plan_name.ilike(search_term),
                    FDPlan.description.ilike(search_term),
                    Bank.name.ilike(search_term),
                    Bank.code.ilike(search_term)
                )
            )
        
        if filters.bank_id:
            query = query.filter(FDPlan.bank_id == filters.bank_id)
        
        if filters.is_active is not None:
            query = query.filter(FDPlan.is_active == filters.is_active)
        
        if filters.min_amount:
            query = query.filter(FDPlan.minimum_amount >= filters.min_amount)
        
        if filters.max_amount:
            query = query.filter(FDPlan.maximum_amount <= filters.max_amount)
        
        if filters.tenure_months:
            query = query.filter(FDPlan.tenure_months == filters.tenure_months)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (filters.page - 1) * filters.per_page
        fd_plans = query.offset(offset).limit(filters.per_page).all()
        
        return fd_plans, total
    
    @staticmethod
    def get_by_bank(db: Session, bank_id: int, active_only: bool = True) -> List[FDPlan]:
        """Get all FD plans for a specific bank"""
        query = db.query(FDPlan).filter(FDPlan.bank_id == bank_id)
        if active_only:
            query = query.filter(FDPlan.is_active == True)
        return query.all()
    
    @staticmethod
    def update(db: Session, fd_plan_id: int, fd_plan_update: FDPlanUpdate) -> Optional[FDPlan]:
        """Update FD plan"""
        fd_plan = db.query(FDPlan).filter(FDPlan.id == fd_plan_id).first()
        if not fd_plan:
            return None
        
        update_data = fd_plan_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(fd_plan, field, value)
        
        db.commit()
        db.refresh(fd_plan)
        return fd_plan
    
    @staticmethod
    def delete(db: Session, fd_plan_id: int) -> bool:
        """Delete FD plan"""
        fd_plan = db.query(FDPlan).filter(FDPlan.id == fd_plan_id).first()
        if not fd_plan:
            return False
        
        db.delete(fd_plan)
        db.commit()
        return True


# Interest Rate Condition CRUD Operations
class InterestRateConditionCRUD:
    @staticmethod
    def create(db: Session, condition_data: InterestRateConditionCreate, fd_plan_id: int) -> InterestRateCondition:
        """Create a new interest rate condition"""
        condition_dict = condition_data.dict()
        condition_dict["fd_plan_id"] = fd_plan_id
        db_condition = InterestRateCondition(**condition_dict)
        db.add(db_condition)
        db.commit()
        db.refresh(db_condition)
        return db_condition
    
    @staticmethod
    def get(db: Session, condition_id: int) -> Optional[InterestRateCondition]:
        """Get interest rate condition by ID"""
        return db.query(InterestRateCondition).filter(InterestRateCondition.id == condition_id).first()
    
    @staticmethod
    def get_by_fd_plan(db: Session, fd_plan_id: int) -> List[InterestRateCondition]:
        """Get all interest rate conditions for a specific FD plan"""
        return db.query(InterestRateCondition).filter(
            InterestRateCondition.fd_plan_id == fd_plan_id
        ).order_by(
            InterestRateCondition.condition_type,
            InterestRateCondition.min_tenure_months
        ).all()
    
    @staticmethod
    def update(db: Session, condition_id: int, condition_update: InterestRateConditionUpdate) -> Optional[InterestRateCondition]:
        """Update interest rate condition"""
        condition = db.query(InterestRateCondition).filter(InterestRateCondition.id == condition_id).first()
        if not condition:
            return None
        
        update_data = condition_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(condition, field, value)
        
        db.commit()
        db.refresh(condition)
        return condition
    
    @staticmethod
    def delete(db: Session, condition_id: int) -> bool:
        """Delete interest rate condition"""
        condition = db.query(InterestRateCondition).filter(InterestRateCondition.id == condition_id).first()
        if not condition:
            return False
        
        db.delete(condition)
        db.commit()
        return True
    
    @staticmethod
    def delete_by_fd_plan(db: Session, fd_plan_id: int) -> int:
        """Delete all interest rate conditions for a specific FD plan"""
        deleted_count = db.query(InterestRateCondition).filter(
            InterestRateCondition.fd_plan_id == fd_plan_id
        ).delete()
        db.commit()
        return deleted_count


# Excel Upload CRUD Operations
class ExcelUploadCRUD:
    @staticmethod
    def create(db: Session, upload_data: ExcelUploadCreate, filename: str, file_size: int) -> ExcelUpload:
        """Create a new Excel upload record"""
        upload_dict = upload_data.dict()
        upload_dict.update({
            "filename": filename,
            "file_size": file_size
        })
        db_upload = ExcelUpload(**upload_dict)
        db.add(db_upload)
        db.commit()
        db.refresh(db_upload)
        return db_upload
    
    @staticmethod
    def get(db: Session, upload_id: int) -> Optional[ExcelUpload]:
        """Get Excel upload by ID"""
        return db.query(ExcelUpload).options(
            joinedload(ExcelUpload.bank),
            joinedload(ExcelUpload.upload_errors)
        ).filter(ExcelUpload.id == upload_id).first()
    
    @staticmethod
    def get_by_bank(db: Session, bank_id: int, limit: int = 10) -> List[ExcelUpload]:
        """Get recent Excel uploads for a specific bank"""
        return db.query(ExcelUpload).filter(
            ExcelUpload.bank_id == bank_id
        ).order_by(ExcelUpload.uploaded_at.desc()).limit(limit).all()
    
    @staticmethod
    def update_status(db: Session, upload_id: int, status: str, **kwargs) -> Optional[ExcelUpload]:
        """Update upload status and related fields"""
        upload = db.query(ExcelUpload).filter(ExcelUpload.id == upload_id).first()
        if not upload:
            return None
        
        upload.upload_status = status
        for field, value in kwargs.items():
            if hasattr(upload, field):
                setattr(upload, field, value)
        
        db.commit()
        db.refresh(upload)
        return upload
    
    @staticmethod
    def add_error(db: Session, upload_id: int, row_number: int, error_message: str, 
                  column_name: str = None, row_data: Dict[str, Any] = None) -> UploadError:
        """Add an error record for Excel upload"""
        db_error = UploadError(
            upload_id=upload_id,
            row_number=row_number,
            column_name=column_name,
            error_message=error_message,
            row_data=row_data
        )
        db.add(db_error)
        db.commit()
        db.refresh(db_error)
        return db_error


# Utility functions
def get_applicable_interest_rate(db: Session, fd_plan_id: int, withdrawal_months: int) -> Optional[Dict[str, Any]]:
    """Get applicable interest rate for a given withdrawal period"""
    conditions = InterestRateConditionCRUD.get_by_fd_plan(db, fd_plan_id)
    
    # Check for maturity condition
    maturity_condition = next((c for c in conditions if c.condition_type == 'maturity'), None)
    
    # Check for premature conditions
    applicable_premature = None
    for condition in conditions:
        if condition.condition_type == 'premature':
            if (condition.min_tenure_months <= withdrawal_months and 
                (condition.max_tenure_months is None or withdrawal_months < condition.max_tenure_months)):
                applicable_premature = condition
                break
    
    # Get FD plan for base rate
    fd_plan = FDPlanCRUD.get(db, fd_plan_id)
    if not fd_plan:
        return None
    
    if withdrawal_months >= fd_plan.tenure_months and maturity_condition:
        # Maturity case
        return {
            "condition_type": "maturity",
            "interest_rate": float(maturity_condition.interest_rate),
            "penalty_rate": 0.0,
            "penalty_amount": 0.0,
            "description": maturity_condition.description
        }
    elif applicable_premature:
        # Premature case
        return {
            "condition_type": "premature",
            "interest_rate": float(applicable_premature.interest_rate),
            "penalty_rate": float(applicable_premature.penalty_rate),
            "penalty_amount": float(applicable_premature.penalty_amount),
            "description": applicable_premature.description
        }
    else:
        # Default to base rate with penalties
        return {
            "condition_type": "default",
            "interest_rate": float(fd_plan.base_interest_rate),
            "penalty_rate": 1.0,  # 1% default penalty
            "penalty_amount": 0.0,
            "description": "Default rate with penalty for early withdrawal"
        }