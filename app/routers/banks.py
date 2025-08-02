from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.crud import BankCRUD
from app.schemas import (
    Bank, BankCreate, BankUpdate, BankFilter,
    Response, PaginatedResponse
)

router = APIRouter(prefix="/banks", tags=["Banks"])


@router.post("/", response_model=Response, status_code=status.HTTP_201_CREATED)
async def create_bank(
    bank_data: BankCreate,
    db: Session = Depends(get_db)
):
    """Create a new bank"""
    try:
        # Check if bank with same name or code already exists
        existing_bank_name = BankCRUD.get_by_name(db, bank_data.name)
        if existing_bank_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bank with name '{bank_data.name}' already exists"
            )
        
        existing_bank_code = BankCRUD.get_by_code(db, bank_data.code)
        if existing_bank_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bank with code '{bank_data.code}' already exists"
            )
        
        # Create bank
        bank = BankCRUD.create(db, bank_data)
        
        return Response(
            success=True,
            message="Bank created successfully",
            data=Bank.from_orm(bank)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bank: {str(e)}"
        )


@router.get("/", response_model=PaginatedResponse)
async def get_banks(
    search: str = Query(None, description="Search by bank name, code, or contact person"),
    is_active: bool = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get list of banks with filtering and pagination"""
    try:
        filters = BankFilter(
            search=search,
            is_active=is_active,
            page=page,
            per_page=per_page
        )
        
        banks, total = BankCRUD.get_list(db, filters)
        
        # Calculate pagination info
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            success=True,
            message="Banks retrieved successfully",
            data=[Bank.from_orm(bank) for bank in banks],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve banks: {str(e)}"
        )


@router.get("/{bank_id}", response_model=Response)
async def get_bank(
    bank_id: int,
    db: Session = Depends(get_db)
):
    """Get bank by ID"""
    bank = BankCRUD.get(db, bank_id)
    if not bank:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank not found"
        )
    
    return Response(
        success=True,
        message="Bank retrieved successfully",
        data=Bank.from_orm(bank)
    )


@router.put("/{bank_id}", response_model=Response)
async def update_bank(
    bank_id: int,
    bank_update: BankUpdate,
    db: Session = Depends(get_db)
):
    """Update bank information"""
    try:
        # Check if bank exists
        existing_bank = BankCRUD.get(db, bank_id)
        if not existing_bank:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank not found"
            )
        
        # Check for duplicate name/code if being updated
        if bank_update.name and bank_update.name != existing_bank.name:
            duplicate_name = BankCRUD.get_by_name(db, bank_update.name)
            if duplicate_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bank with name '{bank_update.name}' already exists"
                )
        
        if bank_update.code and bank_update.code != existing_bank.code:
            duplicate_code = BankCRUD.get_by_code(db, bank_update.code)
            if duplicate_code:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bank with code '{bank_update.code}' already exists"
                )
        
        # Update bank
        updated_bank = BankCRUD.update(db, bank_id, bank_update)
        
        return Response(
            success=True,
            message="Bank updated successfully",
            data=Bank.from_orm(updated_bank)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update bank: {str(e)}"
        )


@router.delete("/{bank_id}", response_model=Response)
async def delete_bank(
    bank_id: int,
    db: Session = Depends(get_db)
):
    """Delete bank"""
    try:
        success = BankCRUD.delete(db, bank_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank not found"
            )
        
        return Response(
            success=True,
            message="Bank deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete bank: {str(e)}"
        )


@router.patch("/{bank_id}/toggle-active", response_model=Response)
async def toggle_bank_active(
    bank_id: int,
    db: Session = Depends(get_db)
):
    """Toggle bank active status"""
    try:
        bank = BankCRUD.toggle_active(db, bank_id)
        if not bank:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank not found"
            )
        
        status_text = "activated" if bank.is_active else "deactivated"
        return Response(
            success=True,
            message=f"Bank {status_text} successfully",
            data=Bank.from_orm(bank)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle bank status: {str(e)}"
        )


@router.get("/{bank_id}/fd-plans", response_model=Response)
async def get_bank_fd_plans(
    bank_id: int,
    active_only: bool = Query(True, description="Show only active FD plans"),
    db: Session = Depends(get_db)
):
    """Get all FD plans for a specific bank"""
    try:
        # Check if bank exists
        bank = BankCRUD.get(db, bank_id)
        if not bank:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank not found"
            )
        
        from app.crud import FDPlanCRUD
        from app.schemas import FDPlan
        
        fd_plans = FDPlanCRUD.get_by_bank(db, bank_id, active_only)
        
        return Response(
            success=True,
            message="FD plans retrieved successfully",
            data=[FDPlan.from_orm(plan) for plan in fd_plans]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FD plans: {str(e)}"
        )