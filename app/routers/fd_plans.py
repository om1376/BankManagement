from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from decimal import Decimal

from app.database import get_db
from app.crud import FDPlanCRUD, InterestRateConditionCRUD, BankCRUD, get_applicable_interest_rate
from app.schemas import (
    FDPlan, FDPlanCreate, FDPlanUpdate, FDPlanFilter,
    InterestRateCondition, InterestRateConditionCreate, InterestRateConditionUpdate,
    Response, PaginatedResponse
)

router = APIRouter(prefix="/fd-plans", tags=["FD Plans"])


@router.post("/", response_model=Response, status_code=status.HTTP_201_CREATED)
async def create_fd_plan(
    fd_plan_data: FDPlanCreate,
    db: Session = Depends(get_db)
):
    """Create a new FD plan with interest rate conditions"""
    try:
        # Check if bank exists
        bank = BankCRUD.get(db, fd_plan_data.bank_id)
        if not bank:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank not found"
            )
        
        # Check if plan name already exists for this bank
        existing_plans = FDPlanCRUD.get_by_bank(db, fd_plan_data.bank_id, active_only=False)
        if any(plan.plan_name == fd_plan_data.plan_name for plan in existing_plans):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FD plan with name '{fd_plan_data.plan_name}' already exists for this bank"
            )
        
        # Create FD plan
        fd_plan = FDPlanCRUD.create(db, fd_plan_data)
        
        return Response(
            success=True,
            message="FD plan created successfully",
            data=FDPlan.from_orm(fd_plan)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create FD plan: {str(e)}"
        )


@router.get("/", response_model=PaginatedResponse)
async def get_fd_plans(
    search: str = Query(None, description="Search by plan name, description, or bank name"),
    bank_id: int = Query(None, description="Filter by bank ID"),
    is_active: bool = Query(None, description="Filter by active status"),
    min_amount: Decimal = Query(None, description="Minimum amount filter"),
    max_amount: Decimal = Query(None, description="Maximum amount filter"),
    tenure_months: int = Query(None, description="Filter by tenure in months"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get list of FD plans with filtering and pagination"""
    try:
        filters = FDPlanFilter(
            search=search,
            bank_id=bank_id,
            is_active=is_active,
            min_amount=min_amount,
            max_amount=max_amount,
            tenure_months=tenure_months,
            page=page,
            per_page=per_page
        )
        
        fd_plans, total = FDPlanCRUD.get_list(db, filters)
        
        # Calculate pagination info
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            success=True,
            message="FD plans retrieved successfully",
            data=[FDPlan.from_orm(plan) for plan in fd_plans],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve FD plans: {str(e)}"
        )


@router.get("/{fd_plan_id}", response_model=Response)
async def get_fd_plan(
    fd_plan_id: int,
    db: Session = Depends(get_db)
):
    """Get FD plan by ID with all details"""
    fd_plan = FDPlanCRUD.get(db, fd_plan_id)
    if not fd_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="FD plan not found"
        )
    
    return Response(
        success=True,
        message="FD plan retrieved successfully",
        data=FDPlan.from_orm(fd_plan)
    )


@router.put("/{fd_plan_id}", response_model=Response)
async def update_fd_plan(
    fd_plan_id: int,
    fd_plan_update: FDPlanUpdate,
    db: Session = Depends(get_db)
):
    """Update FD plan information"""
    try:
        # Check if FD plan exists
        existing_plan = FDPlanCRUD.get(db, fd_plan_id)
        if not existing_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FD plan not found"
            )
        
        # Check for duplicate plan name within the same bank
        if fd_plan_update.plan_name and fd_plan_update.plan_name != existing_plan.plan_name:
            bank_plans = FDPlanCRUD.get_by_bank(db, existing_plan.bank_id, active_only=False)
            if any(plan.plan_name == fd_plan_update.plan_name and plan.id != fd_plan_id 
                   for plan in bank_plans):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"FD plan with name '{fd_plan_update.plan_name}' already exists for this bank"
                )
        
        # Update FD plan
        updated_plan = FDPlanCRUD.update(db, fd_plan_id, fd_plan_update)
        
        return Response(
            success=True,
            message="FD plan updated successfully",
            data=FDPlan.from_orm(updated_plan)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update FD plan: {str(e)}"
        )


@router.delete("/{fd_plan_id}", response_model=Response)
async def delete_fd_plan(
    fd_plan_id: int,
    db: Session = Depends(get_db)
):
    """Delete FD plan"""
    try:
        success = FDPlanCRUD.delete(db, fd_plan_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FD plan not found"
            )
        
        return Response(
            success=True,
            message="FD plan deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete FD plan: {str(e)}"
        )


# Interest Rate Condition endpoints
@router.post("/{fd_plan_id}/conditions", response_model=Response, status_code=status.HTTP_201_CREATED)
async def create_interest_condition(
    fd_plan_id: int,
    condition_data: InterestRateConditionCreate,
    db: Session = Depends(get_db)
):
    """Create a new interest rate condition for an FD plan"""
    try:
        # Check if FD plan exists
        fd_plan = FDPlanCRUD.get(db, fd_plan_id)
        if not fd_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FD plan not found"
            )
        
        # Create condition
        condition = InterestRateConditionCRUD.create(db, condition_data, fd_plan_id)
        
        return Response(
            success=True,
            message="Interest rate condition created successfully",
            data=InterestRateCondition.from_orm(condition)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create interest rate condition: {str(e)}"
        )


@router.get("/{fd_plan_id}/conditions", response_model=Response)
async def get_fd_plan_conditions(
    fd_plan_id: int,
    db: Session = Depends(get_db)
):
    """Get all interest rate conditions for an FD plan"""
    try:
        # Check if FD plan exists
        fd_plan = FDPlanCRUD.get(db, fd_plan_id)
        if not fd_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FD plan not found"
            )
        
        conditions = InterestRateConditionCRUD.get_by_fd_plan(db, fd_plan_id)
        
        return Response(
            success=True,
            message="Interest rate conditions retrieved successfully",
            data=[InterestRateCondition.from_orm(condition) for condition in conditions]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve interest rate conditions: {str(e)}"
        )


@router.put("/conditions/{condition_id}", response_model=Response)
async def update_interest_condition(
    condition_id: int,
    condition_update: InterestRateConditionUpdate,
    db: Session = Depends(get_db)
):
    """Update interest rate condition"""
    try:
        updated_condition = InterestRateConditionCRUD.update(db, condition_id, condition_update)
        if not updated_condition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest rate condition not found"
            )
        
        return Response(
            success=True,
            message="Interest rate condition updated successfully",
            data=InterestRateCondition.from_orm(updated_condition)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update interest rate condition: {str(e)}"
        )


@router.delete("/conditions/{condition_id}", response_model=Response)
async def delete_interest_condition(
    condition_id: int,
    db: Session = Depends(get_db)
):
    """Delete interest rate condition"""
    try:
        success = InterestRateConditionCRUD.delete(db, condition_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interest rate condition not found"
            )
        
        return Response(
            success=True,
            message="Interest rate condition deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete interest rate condition: {str(e)}"
        )


# Interest calculation endpoints
@router.get("/{fd_plan_id}/calculate-interest", response_model=Response)
async def calculate_interest(
    fd_plan_id: int,
    principal_amount: Decimal = Query(..., description="Principal amount invested"),
    withdrawal_months: int = Query(..., description="Number of months before withdrawal"),
    db: Session = Depends(get_db)
):
    """Calculate interest for a given investment scenario"""
    try:
        # Check if FD plan exists
        fd_plan = FDPlanCRUD.get(db, fd_plan_id)
        if not fd_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FD plan not found"
            )
        
        # Validate input
        if principal_amount < fd_plan.minimum_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Principal amount must be at least {fd_plan.minimum_amount}"
            )
        
        if fd_plan.maximum_amount and principal_amount > fd_plan.maximum_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Principal amount cannot exceed {fd_plan.maximum_amount}"
            )
        
        if withdrawal_months < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Withdrawal months cannot be negative"
            )
        
        # Get applicable interest rate
        rate_info = get_applicable_interest_rate(db, fd_plan_id, withdrawal_months)
        if not rate_info:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Unable to determine applicable interest rate"
            )
        
        # Calculate interest
        annual_rate = rate_info['interest_rate']
        monthly_rate = annual_rate / 12
        
        # Simple interest calculation
        gross_interest = float(principal_amount) * monthly_rate * withdrawal_months
        
        # Apply penalties
        penalty_amount = float(principal_amount) * rate_info['penalty_rate']
        penalty_fixed = rate_info['penalty_amount']
        total_penalty = penalty_amount + penalty_fixed
        
        net_interest = gross_interest - total_penalty
        maturity_amount = float(principal_amount) + net_interest
        
        calculation_details = {
            'fd_plan': {
                'id': fd_plan.id,
                'plan_name': fd_plan.plan_name,
                'bank_name': fd_plan.bank.name if fd_plan.bank else None,
                'tenure_months': fd_plan.tenure_months
            },
            'investment': {
                'principal_amount': float(principal_amount),
                'withdrawal_months': withdrawal_months,
                'is_premature': withdrawal_months < fd_plan.tenure_months
            },
            'rate_details': rate_info,
            'calculations': {
                'annual_interest_rate': annual_rate,
                'monthly_interest_rate': monthly_rate,
                'gross_interest': gross_interest,
                'penalty_rate_amount': penalty_amount,
                'penalty_fixed_amount': penalty_fixed,
                'total_penalty': total_penalty,
                'net_interest': max(0, net_interest),  # Ensure non-negative
                'maturity_amount': max(float(principal_amount), maturity_amount)  # Ensure at least principal
            }
        }
        
        return Response(
            success=True,
            message="Interest calculated successfully",
            data=calculation_details
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate interest: {str(e)}"
        )