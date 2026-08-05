Write-Host "🌐 Setting up Start Working Remotely..." -ForegroundColor Cyan


# Step 1: Create Virtual Environment
if (-not (Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Step 2: Activate & Install Dependencies
Write-Host "Installing requirements..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt

# Step 3: Run Initial Job Scrape & Vector Matching
Write-Host "Running initial job scrape..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" main_agent.py --scan --query "software engineer"

Write-Host "Running vector matching against resume..." -ForegroundColor Yellow
& ".\venv\Scripts\python.exe" main_agent.py --match --min-score 0.75

Write-Host "`n✅ Setup complete! Launching Web Dashboard at http://localhost:5000" -ForegroundColor Green
& ".\venv\Scripts\python.exe" server.py
