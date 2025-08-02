import os
import tempfile
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import pandas as pd
import io

from app.database import get_db
from app.crud import BankCRUD, ExcelUploadCRUD
from app.schemas import Response, ExcelUpload, ExcelUploadCreate
from app.services.excel_service import ExcelProcessor, generate_excel_template
from app.config import settings

router = APIRouter(prefix="/excel", tags=["Excel Upload"])


@router.post("/upload", response_model=Response, status_code=status.HTTP_201_CREATED)
async def upload_excel_file(
    bank_id: int = Form(..., description="Bank ID for the FD plans"),
    uploaded_by: str = Form(None, description="Name of the person uploading"),
    file: UploadFile = File(..., description="Excel file containing FD plans"),
    db: Session = Depends(get_db)
):
    """Upload and process Excel file containing FD plans"""
    try:
        # Validate bank exists
        bank = BankCRUD.get(db, bank_id)
        if not bank:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank not found"
            )
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded"
            )
        
        # Check file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.allowed_file_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format. Allowed formats: {', '.join(settings.allowed_file_extensions)}"
            )
        
        # Check file size
        file_size = 0
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > settings.max_file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum limit of {settings.max_file_size} bytes"
            )
        
        # Create upload record
        upload_data = ExcelUploadCreate(bank_id=bank_id, uploaded_by=uploaded_by)
        upload_record = ExcelUploadCRUD.create(db, upload_data, file.filename, file_size)
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Process the file
            processor = ExcelProcessor(db)
            results = processor.process_file(temp_file_path, upload_record.id, bank_id)
            
            return Response(
                success=True,
                message="File uploaded and processed successfully",
                data={
                    'upload_id': upload_record.id,
                    'filename': file.filename,
                    'bank_id': bank_id,
                    'processing_results': results
                }
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process file: {str(e)}"
        )


@router.get("/template", response_class=StreamingResponse)
async def download_excel_template():
    """Download Excel template for FD plan uploads"""
    try:
        # Generate template
        template_df = generate_excel_template()
        
        # Create Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Main sheet with FD plan data
            template_df.to_excel(writer, sheet_name='FD_Plans', index=False)
            
            # Instructions sheet
            instructions_data = {
                'Column': [
                    'plan_name',
                    'minimum_amount',
                    'maximum_amount',
                    'tenure_months',
                    'base_interest_rate',
                    'description',
                    'premature_conditions'
                ],
                'Description': [
                    'Name of the FD plan (required)',
                    'Minimum investment amount (required)',
                    'Maximum investment amount (optional)',
                    'Tenure in months (required)',
                    'Base interest rate as percentage (required)',
                    'Plan description (optional)',
                    'JSON array of premature withdrawal conditions (optional)'
                ],
                'Format': [
                    'Text',
                    'Number (e.g., 100000)',
                    'Number (e.g., 10000000)',
                    'Integer (e.g., 12)',
                    'Decimal (e.g., 7.5)',
                    'Text',
                    'JSON string (see example)'
                ],
                'Example': [
                    'Regular FD Plan',
                    '100000',
                    '10000000',
                    '12',
                    '7.0',
                    'Standard fixed deposit plan',
                    'See example in data sheet'
                ]
            }
            
            instructions_df = pd.DataFrame(instructions_data)
            instructions_df.to_excel(writer, sheet_name='Instructions', index=False)
            
            # JSON format explanation
            json_explanation_data = {
                'Field': [
                    'condition_type',
                    'min_tenure_months',
                    'max_tenure_months',
                    'interest_rate',
                    'penalty_rate',
                    'description'
                ],
                'Description': [
                    'Always "premature" for early withdrawal conditions',
                    'Minimum months for this condition to apply',
                    'Maximum months for this condition (optional)',
                    'Interest rate for this condition',
                    'Penalty rate to be deducted',
                    'Description of the condition'
                ],
                'Example_Value': [
                    'premature',
                    '0',
                    '1',
                    '6.0',
                    '0.5',
                    'Withdrawal within 1 month'
                ]
            }
            
            json_df = pd.DataFrame(json_explanation_data)
            json_df.to_excel(writer, sheet_name='Conditions_Format', index=False)
        
        output.seek(0)
        
        # Return as streaming response
        headers = {
            'Content-Disposition': 'attachment; filename="FD_Plans_Template.xlsx"'
        }
        
        return StreamingResponse(
            io.BytesIO(output.read()),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate template: {str(e)}"
        )


@router.get("/uploads/{upload_id}", response_model=Response)
async def get_upload_details(
    upload_id: int,
    db: Session = Depends(get_db)
):
    """Get details of a specific upload"""
    try:
        upload = ExcelUploadCRUD.get(db, upload_id)
        if not upload:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upload not found"
            )
        
        return Response(
            success=True,
            message="Upload details retrieved successfully",
            data=ExcelUpload.from_orm(upload)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve upload details: {str(e)}"
        )


@router.get("/uploads", response_model=Response)
async def get_uploads(
    bank_id: int = Query(None, description="Filter by bank ID"),
    status_filter: str = Query(None, description="Filter by upload status"),
    limit: int = Query(20, ge=1, le=100, description="Number of uploads to return"),
    db: Session = Depends(get_db)
):
    """Get list of recent uploads"""
    try:
        if bank_id:
            # Get uploads for specific bank
            uploads = ExcelUploadCRUD.get_by_bank(db, bank_id, limit)
        else:
            # Get all recent uploads (would need to implement this in CRUD)
            uploads = []  # Placeholder
        
        return Response(
            success=True,
            message="Uploads retrieved successfully",
            data=[ExcelUpload.from_orm(upload) for upload in uploads]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve uploads: {str(e)}"
        )


@router.post("/validate", response_model=Response)
async def validate_excel_file(
    file: UploadFile = File(..., description="Excel file to validate"),
    db: Session = Depends(get_db)
):
    """Validate Excel file without processing/saving data"""
    try:
        # Validate file format
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file uploaded"
            )
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in settings.allowed_file_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file format. Allowed formats: {', '.join(settings.allowed_file_extensions)}"
            )
        
        # Read and validate content
        file_content = await file.read()
        
        # Save to temporary file for processing
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            temp_file.write(file_content)
            temp_file_path = temp_file.name
        
        try:
            # Create temporary processor for validation
            processor = ExcelProcessor(db)
            
            # Read and validate file structure
            df = processor._read_excel_file(temp_file_path)
            if df is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to read Excel file"
                )
            
            # Normalize columns
            df = processor._normalize_columns(df)
            
            # Validate columns
            validation_errors = processor._validate_columns(df)
            
            # Validate sample data (first few rows)
            sample_errors = []
            for index, row in df.head(5).iterrows():
                try:
                    processor._parse_fd_plan_row(row, index + 2)
                except Exception as e:
                    sample_errors.append(f"Row {index + 2}: {str(e)}")
            
            validation_result = {
                'filename': file.filename,
                'total_rows': len(df),
                'columns_found': list(df.columns),
                'column_errors': validation_errors,
                'sample_data_errors': sample_errors,
                'is_valid': len(validation_errors) == 0 and len(sample_errors) == 0,
                'sample_data': df.head(3).to_dict('records') if len(df) > 0 else []
            }
            
            return Response(
                success=True,
                message="File validation completed",
                data=validation_result
            )
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate file: {str(e)}"
        )