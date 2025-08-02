-- FD Management Application Database Schema

-- Banks table to store bank information
CREATE TABLE banks (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    code VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- FD Plans table to store fixed deposit plans
CREATE TABLE fd_plans (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    plan_name VARCHAR(255) NOT NULL,
    minimum_amount DECIMAL(15, 2) NOT NULL,
    maximum_amount DECIMAL(15, 2),
    tenure_months INTEGER NOT NULL,
    base_interest_rate DECIMAL(5, 4) NOT NULL, -- Base interest rate on maturity
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bank_id, plan_name)
);

-- Interest rate conditions for premature withdrawals
CREATE TABLE interest_rate_conditions (
    id SERIAL PRIMARY KEY,
    fd_plan_id INTEGER NOT NULL REFERENCES fd_plans(id) ON DELETE CASCADE,
    condition_type VARCHAR(50) NOT NULL, -- 'maturity', 'premature'
    min_tenure_months INTEGER, -- Minimum tenure for this condition (NULL for maturity)
    max_tenure_months INTEGER, -- Maximum tenure for this condition (NULL for maturity)
    interest_rate DECIMAL(5, 4) NOT NULL,
    penalty_rate DECIMAL(5, 4) DEFAULT 0.00, -- Penalty rate to be deducted
    penalty_amount DECIMAL(10, 2) DEFAULT 0.00, -- Fixed penalty amount
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_tenure_range CHECK (
        (condition_type = 'maturity' AND min_tenure_months IS NULL AND max_tenure_months IS NULL) OR
        (condition_type = 'premature' AND min_tenure_months IS NOT NULL)
    )
);

-- Excel upload logs to track file uploads
CREATE TABLE excel_uploads (
    id SERIAL PRIMARY KEY,
    bank_id INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    upload_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    total_rows INTEGER,
    successful_rows INTEGER DEFAULT 0,
    failed_rows INTEGER DEFAULT 0,
    error_details TEXT,
    uploaded_by VARCHAR(255),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Upload errors to track specific row-level errors during Excel processing
CREATE TABLE upload_errors (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER NOT NULL REFERENCES excel_uploads(id) ON DELETE CASCADE,
    row_number INTEGER NOT NULL,
    column_name VARCHAR(100),
    error_message TEXT NOT NULL,
    row_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_banks_code ON banks(code);
CREATE INDEX idx_banks_active ON banks(is_active);
CREATE INDEX idx_fd_plans_bank_id ON fd_plans(bank_id);
CREATE INDEX idx_fd_plans_active ON fd_plans(is_active);
CREATE INDEX idx_interest_conditions_fd_plan_id ON interest_rate_conditions(fd_plan_id);
CREATE INDEX idx_interest_conditions_type ON interest_rate_conditions(condition_type);
CREATE INDEX idx_excel_uploads_bank_id ON excel_uploads(bank_id);
CREATE INDEX idx_excel_uploads_status ON excel_uploads(upload_status);
CREATE INDEX idx_upload_errors_upload_id ON upload_errors(upload_id);

-- Triggers to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_banks_updated_at BEFORE UPDATE ON banks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fd_plans_updated_at BEFORE UPDATE ON fd_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Sample data for testing
INSERT INTO banks (name, code, description, contact_person, email, phone) VALUES
('State Bank of India', 'SBI', 'Leading public sector bank in India', 'John Doe', 'john.doe@sbi.co.in', '+91-11-12345678'),
('HDFC Bank', 'HDFC', 'Private sector bank with extensive network', 'Jane Smith', 'jane.smith@hdfcbank.com', '+91-22-87654321');

-- Sample FD plan
INSERT INTO fd_plans (bank_id, plan_name, minimum_amount, maximum_amount, tenure_months, base_interest_rate, description) VALUES
(1, 'SBI Regular FD', 100000.00, 10000000.00, 12, 0.0700, 'Regular fixed deposit plan with flexible tenure');

-- Sample interest rate conditions
INSERT INTO interest_rate_conditions (fd_plan_id, condition_type, min_tenure_months, max_tenure_months, interest_rate, penalty_rate, description) VALUES
(1, 'maturity', NULL, NULL, 0.0700, 0.0000, 'Interest rate on maturity completion'),
(1, 'premature', 0, 1, 0.0600, 0.0050, 'Interest rate for withdrawal within 1 month with 0.5% penalty'),
(1, 'premature', 1, 3, 0.0625, 0.0025, 'Interest rate for withdrawal within 3 months with 0.25% penalty'),
(1, 'premature', 3, 6, 0.0650, 0.0010, 'Interest rate for withdrawal within 6 months with 0.1% penalty');