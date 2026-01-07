# GymLife Application Startup Script
# Run this script to start the GymLife web application

Write-Host "🏋️ Starting GymLife Application..." -ForegroundColor Cyan
Write-Host ""

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\gymlife_complete_env\Scripts\Activate.ps1

# Run the Flask app
Write-Host "Starting Flask server..." -ForegroundColor Green
Write-Host ""
Write-Host "The application will be available at: http://127.0.0.1:5000" -ForegroundColor Magenta
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python app.py
