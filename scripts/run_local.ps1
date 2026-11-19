# Run CloudCommerce Locally (Standalone mode with full monitoring)
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  STARTING CLOUDCOMMERCE STOREFRONT & CLUSTER MONITORING (LOCAL)" -ForegroundColor Yellow
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "Opening web server on http://localhost:8080..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop the server at any time.`n" -ForegroundColor Gray

Start-Process "http://localhost:8080"
python ./app/app.py
