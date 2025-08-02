// FD Management System - Frontend JavaScript

const API_BASE = '/api';
let banks = [];
let fdPlans = [];

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    loadDashboardStats();
    loadBanks();
    loadFDPlans();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Bank search
    document.getElementById('bank-search').addEventListener('input', debounce(function() {
        loadBanks(this.value);
    }, 300));
    
    // FD Plan search
    document.getElementById('fd-plan-search').addEventListener('input', debounce(function() {
        loadFDPlans();
    }, 300));
    
    // FD Plan bank filter
    document.getElementById('fd-plan-bank-filter').addEventListener('change', function() {
        loadFDPlans();
    });
    
    // Excel upload form
    document.getElementById('excel-upload-form').addEventListener('submit', handleExcelUpload);
}

// Utility functions
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function showAlert(message, type = 'info', duration = 5000) {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();
    
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto dismiss after duration
    if (duration > 0) {
        setTimeout(() => {
            const alert = document.getElementById(alertId);
            if (alert) {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }
        }, duration);
    }
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        maximumFractionDigits: 0
    }).format(amount);
}

function formatPercentage(rate) {
    return (rate * 100).toFixed(2) + '%';
}

// API functions
async function apiCall(url, options = {}) {
    try {
        const response = await fetch(API_BASE + url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.message || 'API request failed');
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Dashboard functions
async function loadDashboardStats() {
    try {
        // Load banks count
        const banksResponse = await apiCall('/banks?per_page=1');
        document.getElementById('total-banks').textContent = banksResponse.total || 0;
        
        // Load FD plans count
        const plansResponse = await apiCall('/fd-plans?per_page=1');
        document.getElementById('total-fd-plans').textContent = plansResponse.total || 0;
        
        // Load active plans count
        const activePlansResponse = await apiCall('/fd-plans?is_active=true&per_page=1');
        document.getElementById('active-plans').textContent = activePlansResponse.total || 0;
        
        // Upload count placeholder
        document.getElementById('total-uploads').textContent = '0';
        
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
    }
}

// Bank functions
async function loadBanks(search = '') {
    try {
        const params = new URLSearchParams({
            per_page: 50,
            ...(search && { search })
        });
        
        const response = await apiCall(`/banks?${params}`);
        banks = response.data || [];
        
        renderBanksTable(banks);
        populateBankSelects(banks);
        
    } catch (error) {
        console.error('Error loading banks:', error);
        showAlert('Error loading banks: ' + error.message, 'danger');
    }
}

function renderBanksTable(banksData) {
    const tbody = document.getElementById('banks-table-body');
    
    if (banksData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No banks found</td></tr>';
        return;
    }
    
    tbody.innerHTML = banksData.map(bank => `
        <tr>
            <td>
                <strong>${bank.name}</strong>
                ${bank.description ? `<br><small class="text-muted">${bank.description}</small>` : ''}
            </td>
            <td><code>${bank.code}</code></td>
            <td>
                ${bank.contact_person || '-'}
                ${bank.email ? `<br><small>${bank.email}</small>` : ''}
            </td>
            <td>
                <span class="badge ${bank.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${bank.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editBank(${bank.id})" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-info" onclick="viewBankPlans(${bank.id})" title="View FD Plans">
                        <i class="bi bi-diagram-3"></i>
                    </button>
                    <button class="btn btn-outline-${bank.is_active ? 'warning' : 'success'}" 
                            onclick="toggleBankStatus(${bank.id})" 
                            title="${bank.is_active ? 'Deactivate' : 'Activate'}">
                        <i class="bi bi-${bank.is_active ? 'pause' : 'play'}"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function populateBankSelects(banksData) {
    const activeBanks = banksData.filter(bank => bank.is_active);
    
    // Populate FD plan bank filter
    const bankFilter = document.getElementById('fd-plan-bank-filter');
    bankFilter.innerHTML = '<option value="">All Banks</option>' +
        activeBanks.map(bank => `<option value="${bank.id}">${bank.name}</option>`).join('');
    
    // Populate FD plan form bank select
    const fdBankSelect = document.getElementById('fd-bank');
    fdBankSelect.innerHTML = '<option value="">Select Bank</option>' +
        activeBanks.map(bank => `<option value="${bank.id}">${bank.name}</option>`).join('');
    
    // Populate upload bank select
    const uploadBankSelect = document.getElementById('upload-bank');
    uploadBankSelect.innerHTML = '<option value="">Choose bank...</option>' +
        activeBanks.map(bank => `<option value="${bank.id}">${bank.name}</option>`).join('');
}

async function saveBank() {
    try {
        const formData = {
            name: document.getElementById('bank-name').value.trim(),
            code: document.getElementById('bank-code').value.trim(),
            contact_person: document.getElementById('contact-person').value.trim() || null,
            email: document.getElementById('email').value.trim() || null,
            phone: document.getElementById('phone').value.trim() || null,
            address: document.getElementById('address').value.trim() || null,
            description: document.getElementById('description').value.trim() || null
        };
        
        if (!formData.name || !formData.code) {
            showAlert('Please fill in all required fields', 'warning');
            return;
        }
        
        const response = await apiCall('/banks', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showAlert('Bank created successfully!', 'success');
        
        // Close modal and refresh data
        const modal = bootstrap.Modal.getInstance(document.getElementById('bankModal'));
        modal.hide();
        document.getElementById('bank-form').reset();
        
        loadBanks();
        loadDashboardStats();
        
    } catch (error) {
        showAlert('Error creating bank: ' + error.message, 'danger');
    }
}

async function toggleBankStatus(bankId) {
    try {
        await apiCall(`/banks/${bankId}/toggle-active`, { method: 'PATCH' });
        showAlert('Bank status updated successfully!', 'success');
        loadBanks();
    } catch (error) {
        showAlert('Error updating bank status: ' + error.message, 'danger');
    }
}

// FD Plan functions
async function loadFDPlans() {
    try {
        const search = document.getElementById('fd-plan-search').value;
        const bankId = document.getElementById('fd-plan-bank-filter').value;
        
        const params = new URLSearchParams({
            per_page: 50,
            ...(search && { search }),
            ...(bankId && { bank_id: bankId })
        });
        
        const response = await apiCall(`/fd-plans?${params}`);
        fdPlans = response.data || [];
        
        renderFDPlansTable(fdPlans);
        
    } catch (error) {
        console.error('Error loading FD plans:', error);
        showAlert('Error loading FD plans: ' + error.message, 'danger');
    }
}

function renderFDPlansTable(plansData) {
    const tbody = document.getElementById('fd-plans-table-body');
    
    if (plansData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">No FD plans found</td></tr>';
        return;
    }
    
    tbody.innerHTML = plansData.map(plan => `
        <tr>
            <td>
                <strong>${plan.plan_name}</strong>
                ${plan.description ? `<br><small class="text-muted">${plan.description}</small>` : ''}
            </td>
            <td>
                ${plan.bank ? plan.bank.name : 'N/A'}
                ${plan.bank ? `<br><small class="text-muted">${plan.bank.code}</small>` : ''}
            </td>
            <td>${formatCurrency(plan.minimum_amount)}</td>
            <td>${plan.tenure_months} months</td>
            <td>${formatPercentage(plan.base_interest_rate)}</td>
            <td>
                <span class="badge ${plan.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${plan.is_active ? 'Active' : 'Inactive'}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="editFDPlan(${plan.id})" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-info" onclick="viewInterestConditions(${plan.id})" title="View Conditions">
                        <i class="bi bi-percent"></i>
                    </button>
                    <button class="btn btn-outline-success" onclick="calculateInterest(${plan.id})" title="Calculate Interest">
                        <i class="bi bi-calculator"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

async function saveFDPlan() {
    try {
        const formData = {
            bank_id: parseInt(document.getElementById('fd-bank').value),
            plan_name: document.getElementById('plan-name').value.trim(),
            minimum_amount: parseFloat(document.getElementById('min-amount').value),
            maximum_amount: document.getElementById('max-amount').value ? 
                parseFloat(document.getElementById('max-amount').value) : null,
            tenure_months: parseInt(document.getElementById('tenure').value),
            base_interest_rate: parseFloat(document.getElementById('base-rate').value) / 100,
            description: document.getElementById('plan-description').value.trim() || null,
            interest_conditions: [
                {
                    condition_type: 'maturity',
                    interest_rate: parseFloat(document.getElementById('base-rate').value) / 100,
                    penalty_rate: 0,
                    penalty_amount: 0,
                    description: 'Interest rate on maturity completion'
                }
            ]
        };
        
        if (!formData.bank_id || !formData.plan_name || !formData.minimum_amount || 
            !formData.tenure_months || !formData.base_interest_rate) {
            showAlert('Please fill in all required fields', 'warning');
            return;
        }
        
        const response = await apiCall('/fd-plans', {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        
        showAlert('FD plan created successfully!', 'success');
        
        // Close modal and refresh data
        const modal = bootstrap.Modal.getInstance(document.getElementById('fdPlanModal'));
        modal.hide();
        document.getElementById('fd-plan-form').reset();
        
        loadFDPlans();
        loadDashboardStats();
        
    } catch (error) {
        showAlert('Error creating FD plan: ' + error.message, 'danger');
    }
}

// Excel upload functions
async function handleExcelUpload(event) {
    event.preventDefault();
    
    const bankId = document.getElementById('upload-bank').value;
    const uploadedBy = document.getElementById('uploaded-by').value;
    const fileInput = document.getElementById('excel-file');
    const file = fileInput.files[0];
    
    if (!bankId) {
        showAlert('Please select a bank', 'warning');
        return;
    }
    
    if (!file) {
        showAlert('Please select a file to upload', 'warning');
        return;
    }
    
    // Validate file type
    const allowedTypes = ['.xlsx', '.xls'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!allowedTypes.includes(fileExtension)) {
        showAlert('Invalid file format. Please upload .xlsx or .xls files only.', 'warning');
        return;
    }
    
    try {
        // Show upload progress
        const statusDiv = document.getElementById('upload-status');
        const progressDiv = document.getElementById('upload-progress');
        
        statusDiv.innerHTML = '<i class="bi bi-upload"></i> Uploading file...';
        progressDiv.style.display = 'block';
        progressDiv.querySelector('.progress-bar').style.width = '50%';
        
        // Prepare form data
        const formData = new FormData();
        formData.append('bank_id', bankId);
        formData.append('file', file);
        if (uploadedBy) {
            formData.append('uploaded_by', uploadedBy);
        }
        
        // Upload file
        const response = await fetch(API_BASE + '/excel/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
            throw new Error(result.message || 'Upload failed');
        }
        
        // Update progress
        progressDiv.querySelector('.progress-bar').style.width = '100%';
        
        // Show results
        const processingResults = result.data.processing_results;
        statusDiv.innerHTML = `
            <div class="alert alert-${processingResults.success ? 'success' : 'danger'} mb-0">
                <strong>Upload Complete!</strong><br>
                Total rows: ${processingResults.total_rows || 0}<br>
                Successful: ${processingResults.successful_rows || 0}<br>
                Failed: ${processingResults.failed_rows || 0}
                ${processingResults.errors && processingResults.errors.length > 0 ? 
                    `<br><small>Errors: ${processingResults.errors.length}</small>` : ''}
            </div>
        `;
        
        // Reset form
        document.getElementById('excel-upload-form').reset();
        
        // Refresh data
        setTimeout(() => {
            loadFDPlans();
            loadDashboardStats();
            progressDiv.style.display = 'none';
        }, 2000);
        
        showAlert(
            `File processed successfully! ${processingResults.successful_rows} plans created.`,
            processingResults.success ? 'success' : 'warning'
        );
        
    } catch (error) {
        console.error('Upload error:', error);
        
        document.getElementById('upload-status').innerHTML = `
            <div class="alert alert-danger mb-0">
                <strong>Upload Failed!</strong><br>
                ${error.message}
            </div>
        `;
        
        document.getElementById('upload-progress').style.display = 'none';
        showAlert('Upload failed: ' + error.message, 'danger');
    }
}

async function downloadTemplate() {
    try {
        const response = await fetch(API_BASE + '/excel/template');
        
        if (!response.ok) {
            throw new Error('Failed to download template');
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'FD_Plans_Template.xlsx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        showAlert('Template downloaded successfully!', 'success');
        
    } catch (error) {
        showAlert('Error downloading template: ' + error.message, 'danger');
    }
}

// Placeholder functions for additional features
function editBank(bankId) {
    showAlert('Edit bank functionality coming soon!', 'info');
}

function viewBankPlans(bankId) {
    // Filter FD plans by bank
    document.getElementById('fd-plan-bank-filter').value = bankId;
    loadFDPlans();
    document.getElementById('fd-plans').scrollIntoView({ behavior: 'smooth' });
}

function editFDPlan(planId) {
    showAlert('Edit FD plan functionality coming soon!', 'info');
}

function viewInterestConditions(planId) {
    showAlert('View interest conditions functionality coming soon!', 'info');
}

function calculateInterest(planId) {
    const plan = fdPlans.find(p => p.id === planId);
    if (plan) {
        const amount = prompt('Enter investment amount:');
        const months = prompt('Enter withdrawal after months:');
        
        if (amount && months) {
            // This would typically open a modal with detailed calculation
            showAlert(
                `Interest calculation for ${plan.plan_name} - Amount: ₹${amount}, Period: ${months} months. ` +
                'Detailed calculation feature coming soon!', 
                'info'
            );
        }
    }
}