import pandas as pd
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal, InvalidOperation
from sqlalchemy.orm import Session
from datetime import datetime

from app.crud import FDPlanCRUD, InterestRateConditionCRUD, ExcelUploadCRUD
from app.schemas import FDPlanCreate, InterestRateConditionCreate
from app.models import ExcelUpload


class ExcelProcessor:
    """Service to process Excel files containing FD plan data"""
    
    # Expected column mappings
    REQUIRED_COLUMNS = {
        'plan_name': ['plan_name', 'plan name', 'fd plan name', 'scheme name'],
        'minimum_amount': ['minimum_amount', 'min_amount', 'minimum amount', 'min amount'],
        'maximum_amount': ['maximum_amount', 'max_amount', 'maximum amount', 'max amount'],
        'tenure_months': ['tenure_months', 'tenure', 'tenure in months', 'period'],
        'base_interest_rate': ['base_interest_rate', 'base_rate', 'maturity_rate', 'interest_rate'],
        'description': ['description', 'details', 'plan description']
    }
    
    CONDITION_COLUMNS = {
        'condition_type': ['condition_type', 'type'],
        'min_tenure_months': ['min_tenure_months', 'min_tenure', 'from_months'],
        'max_tenure_months': ['max_tenure_months', 'max_tenure', 'to_months'],
        'interest_rate': ['interest_rate', 'rate'],
        'penalty_rate': ['penalty_rate', 'penalty'],
        'penalty_amount': ['penalty_amount', 'penalty_amount_fixed'],
        'condition_description': ['condition_description', 'condition_desc', 'remarks']
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.errors = []
        self.warnings = []
    
    def process_file(self, file_path: str, upload_id: int, bank_id: int) -> Dict[str, Any]:
        """
        Process Excel file and create FD plans
        
        Args:
            file_path: Path to the Excel file
            upload_id: ID of the upload record
            bank_id: ID of the bank
            
        Returns:
            Dict containing processing results
        """
        try:
            # Update upload status to processing
            ExcelUploadCRUD.update_status(
                self.db, upload_id, 'processing',
                processed_at=datetime.utcnow()
            )
            
            # Read Excel file
            df = self._read_excel_file(file_path)
            if df is None:
                raise ValueError("Failed to read Excel file")
            
            # Normalize column names
            df = self._normalize_columns(df)
            
            # Validate required columns
            validation_errors = self._validate_columns(df)
            if validation_errors:
                raise ValueError(f"Column validation failed: {', '.join(validation_errors)}")
            
            # Process rows
            results = self._process_rows(df, upload_id, bank_id)
            
            # Update upload status
            ExcelUploadCRUD.update_status(
                self.db, upload_id, 'completed',
                total_rows=len(df),
                successful_rows=results['successful_count'],
                failed_rows=results['failed_count']
            )
            
            return {
                'success': True,
                'total_rows': len(df),
                'successful_rows': results['successful_count'],
                'failed_rows': results['failed_count'],
                'created_plans': results['created_plans'],
                'errors': self.errors,
                'warnings': self.warnings
            }
            
        except Exception as e:
            # Update upload status to failed
            ExcelUploadCRUD.update_status(
                self.db, upload_id, 'failed',
                error_details=str(e)
            )
            
            return {
                'success': False,
                'error': str(e),
                'errors': self.errors,
                'warnings': self.warnings
            }
    
    def _read_excel_file(self, file_path: str) -> Optional[pd.DataFrame]:
        """Read Excel file and return DataFrame"""
        try:
            # Try reading as .xlsx first, then .xls
            if file_path.endswith('.xlsx'):
                df = pd.read_excel(file_path, engine='openpyxl')
            else:
                df = pd.read_excel(file_path, engine='xlrd')
            
            # Remove completely empty rows
            df = df.dropna(how='all')
            
            return df
            
        except Exception as e:
            self.errors.append(f"Error reading Excel file: {str(e)}")
            return None
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to match expected format"""
        # Convert column names to lowercase and replace spaces/special chars
        df.columns = df.columns.str.lower().str.replace(' ', '_').str.replace('-', '_')
        
        # Create mapping for known column variations
        column_mapping = {}
        
        for standard_col, variations in {**self.REQUIRED_COLUMNS, **self.CONDITION_COLUMNS}.items():
            for col in df.columns:
                if col in [v.lower().replace(' ', '_') for v in variations]:
                    column_mapping[col] = standard_col
                    break
        
        # Apply mapping
        df = df.rename(columns=column_mapping)
        
        return df
    
    def _validate_columns(self, df: pd.DataFrame) -> List[str]:
        """Validate that required columns are present"""
        errors = []
        required_basic_cols = ['plan_name', 'minimum_amount', 'tenure_months', 'base_interest_rate']
        
        for col in required_basic_cols:
            if col not in df.columns:
                errors.append(f"Required column '{col}' not found")
        
        return errors
    
    def _process_rows(self, df: pd.DataFrame, upload_id: int, bank_id: int) -> Dict[str, Any]:
        """Process each row in the DataFrame"""
        successful_count = 0
        failed_count = 0
        created_plans = []
        
        for index, row in df.iterrows():
            row_number = index + 2  # Excel row number (1-indexed + header)
            
            try:
                # Parse FD plan data
                fd_plan_data = self._parse_fd_plan_row(row, row_number)
                fd_plan_data['bank_id'] = bank_id
                
                # Parse interest rate conditions
                conditions = self._parse_interest_conditions(row, row_number)
                fd_plan_data['interest_conditions'] = conditions
                
                # Create FD plan
                fd_plan_create = FDPlanCreate(**fd_plan_data)
                created_plan = FDPlanCRUD.create(self.db, fd_plan_create)
                
                created_plans.append({
                    'id': created_plan.id,
                    'plan_name': created_plan.plan_name,
                    'row_number': row_number
                })
                
                successful_count += 1
                
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                
                # Log error to database
                ExcelUploadCRUD.add_error(
                    self.db, upload_id, row_number, error_msg,
                    row_data=row.to_dict()
                )
                
                self.errors.append({
                    'row_number': row_number,
                    'error': error_msg,
                    'data': row.to_dict()
                })
        
        return {
            'successful_count': successful_count,
            'failed_count': failed_count,
            'created_plans': created_plans
        }
    
    def _parse_fd_plan_row(self, row: pd.Series, row_number: int) -> Dict[str, Any]:
        """Parse FD plan data from a row"""
        try:
            # Required fields
            plan_name = self._get_string_value(row, 'plan_name', required=True)
            minimum_amount = self._get_decimal_value(row, 'minimum_amount', required=True)
            tenure_months = self._get_integer_value(row, 'tenure_months', required=True)
            base_interest_rate = self._get_decimal_value(row, 'base_interest_rate', required=True)
            
            # Optional fields
            maximum_amount = self._get_decimal_value(row, 'maximum_amount')
            description = self._get_string_value(row, 'description')
            
            # Validate values
            if minimum_amount <= 0:
                raise ValueError("Minimum amount must be greater than 0")
            
            if maximum_amount and maximum_amount < minimum_amount:
                raise ValueError("Maximum amount must be greater than or equal to minimum amount")
            
            if tenure_months <= 0:
                raise ValueError("Tenure must be greater than 0 months")
            
            if base_interest_rate < 0:
                raise ValueError("Interest rate cannot be negative")
            
            return {
                'plan_name': plan_name,
                'minimum_amount': minimum_amount,
                'maximum_amount': maximum_amount,
                'tenure_months': tenure_months,
                'base_interest_rate': base_interest_rate / 100 if base_interest_rate > 1 else base_interest_rate,  # Convert percentage
                'description': description,
                'is_active': True
            }
            
        except Exception as e:
            raise ValueError(f"Row {row_number}: {str(e)}")
    
    def _parse_interest_conditions(self, row: pd.Series, row_number: int) -> List[Dict[str, Any]]:
        """Parse interest rate conditions from row or additional sheets"""
        conditions = []
        
        # Add maturity condition (required)
        maturity_rate = self._get_decimal_value(row, 'base_interest_rate', required=True)
        conditions.append({
            'condition_type': 'maturity',
            'interest_rate': maturity_rate / 100 if maturity_rate > 1 else maturity_rate,
            'penalty_rate': 0.0,
            'penalty_amount': 0.0,
            'description': 'Interest rate on maturity completion'
        })
        
        # Parse premature conditions from JSON or structured columns
        premature_conditions_str = self._get_string_value(row, 'premature_conditions')
        if premature_conditions_str:
            try:
                premature_data = json.loads(premature_conditions_str)
                for condition in premature_data:
                    conditions.append(self._validate_condition(condition))
            except json.JSONDecodeError:
                self.warnings.append(f"Row {row_number}: Invalid JSON in premature_conditions")
        
        # Look for individual condition columns (alternative format)
        condition_columns = [col for col in row.index if col.startswith('condition_')]
        if condition_columns:
            # Parse structured condition data
            # This would handle cases where conditions are in separate columns
            pass
        
        return conditions
    
    def _validate_condition(self, condition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize a single interest rate condition"""
        required_fields = ['condition_type', 'interest_rate']
        for field in required_fields:
            if field not in condition:
                raise ValueError(f"Missing required field '{field}' in condition")
        
        if condition['condition_type'] not in ['maturity', 'premature']:
            raise ValueError("condition_type must be 'maturity' or 'premature'")
        
        # Normalize interest rate
        interest_rate = float(condition['interest_rate'])
        if interest_rate > 1:
            interest_rate = interest_rate / 100
        
        validated_condition = {
            'condition_type': condition['condition_type'],
            'interest_rate': interest_rate,
            'penalty_rate': float(condition.get('penalty_rate', 0.0)),
            'penalty_amount': float(condition.get('penalty_amount', 0.0)),
            'description': condition.get('description', '')
        }
        
        if condition['condition_type'] == 'premature':
            validated_condition['min_tenure_months'] = int(condition.get('min_tenure_months', 0))
            validated_condition['max_tenure_months'] = condition.get('max_tenure_months')
            if validated_condition['max_tenure_months']:
                validated_condition['max_tenure_months'] = int(validated_condition['max_tenure_months'])
        
        return validated_condition
    
    def _get_string_value(self, row: pd.Series, column: str, required: bool = False) -> Optional[str]:
        """Get string value from row with validation"""
        if column not in row.index:
            if required:
                raise ValueError(f"Required column '{column}' not found")
            return None
        
        value = row[column]
        if pd.isna(value):
            if required:
                raise ValueError(f"Required field '{column}' is empty")
            return None
        
        return str(value).strip()
    
    def _get_decimal_value(self, row: pd.Series, column: str, required: bool = False) -> Optional[Decimal]:
        """Get decimal value from row with validation"""
        if column not in row.index:
            if required:
                raise ValueError(f"Required column '{column}' not found")
            return None
        
        value = row[column]
        if pd.isna(value):
            if required:
                raise ValueError(f"Required field '{column}' is empty")
            return None
        
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            raise ValueError(f"Invalid decimal value for '{column}': {value}")
    
    def _get_integer_value(self, row: pd.Series, column: str, required: bool = False) -> Optional[int]:
        """Get integer value from row with validation"""
        if column not in row.index:
            if required:
                raise ValueError(f"Required column '{column}' not found")
            return None
        
        value = row[column]
        if pd.isna(value):
            if required:
                raise ValueError(f"Required field '{column}' is empty")
            return None
        
        try:
            return int(float(value))  # Convert through float first to handle decimal strings
        except (ValueError, TypeError):
            raise ValueError(f"Invalid integer value for '{column}': {value}")


def generate_excel_template() -> pd.DataFrame:
    """Generate Excel template for FD plan uploads"""
    template_data = {
        'plan_name': ['Sample FD Plan 1', 'Sample FD Plan 2'],
        'minimum_amount': [100000, 50000],
        'maximum_amount': [10000000, 5000000],
        'tenure_months': [12, 24],
        'base_interest_rate': [7.0, 7.5],
        'description': [
            'Regular FD plan with flexible tenure',
            'Premium FD plan for higher amounts'
        ],
        'premature_conditions': [
            json.dumps([
                {
                    "condition_type": "premature",
                    "min_tenure_months": 0,
                    "max_tenure_months": 1,
                    "interest_rate": 6.0,
                    "penalty_rate": 0.5,
                    "description": "Withdrawal within 1 month"
                },
                {
                    "condition_type": "premature",
                    "min_tenure_months": 1,
                    "max_tenure_months": 3,
                    "interest_rate": 6.25,
                    "penalty_rate": 0.25,
                    "description": "Withdrawal within 3 months"
                }
            ]),
            json.dumps([
                {
                    "condition_type": "premature",
                    "min_tenure_months": 0,
                    "max_tenure_months": 6,
                    "interest_rate": 6.5,
                    "penalty_rate": 1.0,
                    "description": "Withdrawal within 6 months"
                }
            ])
        ]
    }
    
    return pd.DataFrame(template_data)