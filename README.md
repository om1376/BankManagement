# FD Management System

A comprehensive Fixed Deposit Management Application with bank onboarding, FD plan management, and Excel bulk upload functionality.

## Features

### 🏦 Bank Management
- **Bank Onboarding**: Add new banks with complete details
- **CRUD Operations**: Create, read, update, and delete bank information
- **Status Management**: Activate/deactivate banks
- **Search & Filter**: Find banks quickly with search functionality

### 📊 FD Plan Management
- **Flexible Plans**: Create FD plans with conditional interest rates
- **Interest Rate Conditions**: Define different rates for:
  - Maturity (full tenure completion)
  - Premature withdrawal with various time periods
  - Penalty rates and amounts
- **Comprehensive Validation**: Ensure data integrity
- **Interest Calculator**: Calculate returns based on withdrawal timing

### 📁 Excel Upload System
- **Bulk Import**: Upload FD plans via Excel files
- **Template Generation**: Download standardized Excel templates
- **Data Validation**: Comprehensive validation during upload
- **Error Reporting**: Detailed error tracking for failed rows
- **Processing Status**: Real-time upload progress tracking

### 🎯 Key Capabilities
- **Conditional Interest Rates**: Support for complex interest rate structures
- **Database Schema**: Robust PostgreSQL schema with constraints
- **API Documentation**: Interactive Swagger/OpenAPI documentation
- **Modern UI**: Bootstrap-based responsive frontend
- **Error Handling**: Comprehensive validation and error management

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **File Processing**: pandas, openpyxl
- **Validation**: Pydantic
- **API Documentation**: Swagger/OpenAPI

## Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- pip (Python package installer)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd fd-management
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Database Setup
1. Create a PostgreSQL database:
```sql
CREATE DATABASE fd_management;
```

2. Update the `.env` file with your database credentials:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/fd_management
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=fd_management
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password
```

3. Run the database schema:
```bash
psql -U your_username -d fd_management -f database/schema.sql
```

### 4. Start the Application
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The application will be available at:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc

## Usage Guide

### Bank Onboarding
1. Navigate to the Banks section
2. Click "Add New Bank"
3. Fill in bank details (name, code, contact info)
4. Save to add the bank to the system

### Creating FD Plans
1. Go to FD Plans section
2. Click "Add FD Plan"
3. Select bank and enter plan details:
   - Plan name
   - Minimum/maximum amounts
   - Tenure in months
   - Base interest rate
4. The system automatically creates maturity conditions

### Excel Upload Process
1. Download the Excel template
2. Fill in FD plan data following the template format
3. For conditional interest rates, use JSON format in the `premature_conditions` column:
```json
[
  {
    "condition_type": "premature",
    "min_tenure_months": 0,
    "max_tenure_months": 1,
    "interest_rate": 6.0,
    "penalty_rate": 0.5,
    "description": "Withdrawal within 1 month"
  }
]
```
4. Upload the file and monitor processing status

## Database Schema

### Banks Table
- Basic bank information
- Contact details
- Status management

### FD Plans Table
- Plan details with tenure and amounts
- Base interest rate
- Bank association

### Interest Rate Conditions Table
- Flexible condition definitions
- Maturity vs premature withdrawal rates
- Penalty configurations

### Excel Upload Tracking
- Upload history and status
- Error logging for failed rows
- Processing statistics

## API Endpoints

### Banks
- `POST /api/banks` - Create new bank
- `GET /api/banks` - List banks with filtering
- `GET /api/banks/{id}` - Get bank details
- `PUT /api/banks/{id}` - Update bank
- `DELETE /api/banks/{id}` - Delete bank
- `PATCH /api/banks/{id}/toggle-active` - Toggle status

### FD Plans
- `POST /api/fd-plans` - Create FD plan
- `GET /api/fd-plans` - List plans with filtering
- `GET /api/fd-plans/{id}` - Get plan details
- `PUT /api/fd-plans/{id}` - Update plan
- `DELETE /api/fd-plans/{id}` - Delete plan
- `GET /api/fd-plans/{id}/calculate-interest` - Calculate returns

### Excel Upload
- `POST /api/excel/upload` - Upload Excel file
- `GET /api/excel/template` - Download template
- `POST /api/excel/validate` - Validate file without processing
- `GET /api/excel/uploads/{id}` - Get upload details

## Interest Rate Example

For an FD plan with ₹100,000 minimum, 12-month tenure, 7% base rate:

### Conditional Rates:
- **Maturity (12 months)**: 7% (no penalty)
- **Withdrawal within 1 month**: 6% + 0.5% penalty
- **Withdrawal within 3 months**: 6.25% + 0.25% penalty  
- **Withdrawal within 6 months**: 6.5% + 0.1% penalty

### Calculation Example:
- Principal: ₹100,000
- Withdrawal after 6 months
- Applicable rate: 6.5% annual
- Penalty: 0.1% of principal = ₹100
- Interest: ₹100,000 × 6.5% × 6/12 = ₹3,250
- Final amount: ₹100,000 + ₹3,250 - ₹100 = ₹103,150

## Development

### Project Structure
```
fd-management/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── database.py          # Database connection
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── crud.py              # Database operations
│   ├── routers/             # API route handlers
│   │   ├── banks.py
│   │   ├── fd_plans.py
│   │   └── excel_upload.py
│   └── services/            # Business logic
│       └── excel_service.py
├── database/
│   └── schema.sql           # Database schema
├── static/                  # Frontend files
│   ├── index.html
│   └── js/app.js
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables
└── README.md               # This file
```

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black app/

# Check imports
isort app/

# Lint
flake8 app/
```

## Configuration

Key environment variables in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/fd_management

# Application
APP_NAME=FD Management System
DEBUG=True
HOST=0.0.0.0
PORT=8000

# File Upload
MAX_FILE_SIZE=10485760
ALLOWED_FILE_EXTENSIONS=.xlsx,.xls
UPLOAD_FOLDER=uploads

# Security
SECRET_KEY=your-secret-key-change-in-production
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the API documentation at `/docs`
- Review the database schema in `database/schema.sql`
- Examine example Excel templates generated by the system
