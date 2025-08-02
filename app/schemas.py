from typing import List, Optional, Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field, validator


# Bank Schemas
class BankBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    is_active: bool = True


class BankCreate(BankBase):
    pass


class BankUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = None
    contact_person: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = None
    is_active: Optional[bool] = None


class Bank(BankBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Interest Rate Condition Schemas
class InterestRateConditionBase(BaseModel):
    condition_type: str = Field(..., regex="^(maturity|premature)$")
    min_tenure_months: Optional[int] = Field(None, ge=0)
    max_tenure_months: Optional[int] = Field(None, ge=0)
    interest_rate: Decimal = Field(..., ge=0, decimal_places=4)
    penalty_rate: Decimal = Field(default=Decimal('0.00'), ge=0, decimal_places=4)
    penalty_amount: Decimal = Field(default=Decimal('0.00'), ge=0, decimal_places=2)
    description: Optional[str] = None
    
    @validator('max_tenure_months')
    def validate_tenure_range(cls, v, values):
        if 'min_tenure_months' in values and values['min_tenure_months'] is not None and v is not None:
            if v < values['min_tenure_months']:
                raise ValueError('max_tenure_months must be greater than or equal to min_tenure_months')
        return v
    
    @validator('min_tenure_months', 'max_tenure_months')
    def validate_maturity_conditions(cls, v, values):
        if 'condition_type' in values:
            if values['condition_type'] == 'maturity' and v is not None:
                raise ValueError('maturity conditions should not have tenure limits')
            elif values['condition_type'] == 'premature' and 'min_tenure_months' in values and values['min_tenure_months'] is None:
                raise ValueError('premature conditions must have min_tenure_months')
        return v


class InterestRateConditionCreate(InterestRateConditionBase):
    pass


class InterestRateConditionUpdate(BaseModel):
    condition_type: Optional[str] = Field(None, regex="^(maturity|premature)$")
    min_tenure_months: Optional[int] = Field(None, ge=0)
    max_tenure_months: Optional[int] = Field(None, ge=0)
    interest_rate: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    penalty_rate: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    penalty_amount: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    description: Optional[str] = None


class InterestRateCondition(InterestRateConditionBase):
    id: int
    fd_plan_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# FD Plan Schemas
class FDPlanBase(BaseModel):
    plan_name: str = Field(..., min_length=1, max_length=255)
    minimum_amount: Decimal = Field(..., gt=0, decimal_places=2)
    maximum_amount: Optional[Decimal] = Field(None, decimal_places=2)
    tenure_months: int = Field(..., gt=0)
    base_interest_rate: Decimal = Field(..., ge=0, decimal_places=4)
    description: Optional[str] = None
    is_active: bool = True
    
    @validator('maximum_amount')
    def validate_maximum_amount(cls, v, values):
        if v is not None and 'minimum_amount' in values and v < values['minimum_amount']:
            raise ValueError('maximum_amount must be greater than or equal to minimum_amount')
        return v


class FDPlanCreate(FDPlanBase):
    bank_id: int
    interest_conditions: List[InterestRateConditionCreate] = []


class FDPlanUpdate(BaseModel):
    plan_name: Optional[str] = Field(None, min_length=1, max_length=255)
    minimum_amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    maximum_amount: Optional[Decimal] = Field(None, decimal_places=2)
    tenure_months: Optional[int] = Field(None, gt=0)
    base_interest_rate: Optional[Decimal] = Field(None, ge=0, decimal_places=4)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class FDPlan(FDPlanBase):
    id: int
    bank_id: int
    created_at: datetime
    updated_at: datetime
    bank: Optional[Bank] = None
    interest_conditions: List[InterestRateCondition] = []
    
    class Config:
        from_attributes = True


class FDPlanSummary(BaseModel):
    id: int
    plan_name: str
    minimum_amount: Decimal
    maximum_amount: Optional[Decimal]
    tenure_months: int
    base_interest_rate: Decimal
    is_active: bool
    bank_name: str
    bank_code: str
    conditions_count: int
    
    class Config:
        from_attributes = True


# Excel Upload Schemas
class ExcelUploadCreate(BaseModel):
    bank_id: int
    uploaded_by: Optional[str] = None


class ExcelUpload(BaseModel):
    id: int
    bank_id: int
    filename: str
    file_size: Optional[int]
    upload_status: str
    total_rows: Optional[int]
    successful_rows: int
    failed_rows: int
    error_details: Optional[str]
    uploaded_by: Optional[str]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    bank: Optional[Bank] = None
    
    class Config:
        from_attributes = True


class UploadError(BaseModel):
    id: int
    upload_id: int
    row_number: int
    column_name: Optional[str]
    error_message: str
    row_data: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Excel Template Schema
class ExcelRowData(BaseModel):
    plan_name: str
    minimum_amount: Decimal
    maximum_amount: Optional[Decimal]
    tenure_months: int
    base_interest_rate: Decimal
    description: Optional[str]
    # Interest conditions as JSON string or structured data
    maturity_rate: Decimal
    premature_conditions: Optional[str]  # JSON string of conditions


# Response Schemas
class Response(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class PaginatedResponse(Response):
    total: int
    page: int
    per_page: int
    pages: int


# Search and Filter Schemas
class BankFilter(BaseModel):
    search: Optional[str] = None
    is_active: Optional[bool] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)


class FDPlanFilter(BaseModel):
    search: Optional[str] = None
    bank_id: Optional[int] = None
    is_active: Optional[bool] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    tenure_months: Optional[int] = None
    page: int = Field(default=1, ge=1)
    per_page: int = Field(default=10, ge=1, le=100)