# GreenLoop AI Setup Script
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "      Initializing GreenLoop AI...     " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Ensure venv is active or call its interpreter
$PythonPath = ".\venv\Scripts\python.exe"
$PipPath = ".\venv\Scripts\pip.exe"

if (-not (Test-Path $PythonPath)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

Write-Host "Upgrading pip and installing requirements..." -ForegroundColor Yellow
& $PipPath install --upgrade pip
& $PipPath install -r requirements.txt

Write-Host "Generating database migrations..." -ForegroundColor Yellow
& $PythonPath manage.py makemigrations users reports missions

Write-Host "Applying migrations..." -ForegroundColor Yellow
& $PythonPath manage.py migrate

Write-Host "Seeding database with default badges, users, and reports..." -ForegroundColor Yellow
& $PythonPath manage.py shell -c "import scripts.seed_db; scripts.seed_db.seed()"

Write-Host "Running test suite to verify platform security and classification..." -ForegroundColor Yellow
& $PythonPath manage.py test

Write-Host "========================================" -ForegroundColor Green
Write-Host "   GreenLoop AI successfully initialized! " -ForegroundColor Green
Write-Host "   Start dev server: .\venv\Scripts\python.exe manage.py runserver" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
