# Project Dashboard - Installation Script
# Run this script to set up the dashboard for first-time use.

param(
    [switch]$WithStartup,  # Add to Windows startup
    [switch]$BuildOnly     # Only build, don't launch
)

$ErrorActionPreference = "Stop"

Write-Host "=== Project Dashboard Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check for Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "ERROR: Python not found. Please install Python 3.12+" -ForegroundColor Red
    exit 1
}

# Check Python version
$pyVersion = python --version 2>&1
Write-Host "Found: $pyVersion" -ForegroundColor Green

# Check for uv
$uvCmd = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvCmd) {
    Write-Host "Installing uv package manager..." -ForegroundColor Yellow
    irm https://astral.sh/uv/install.ps1 | iex
}

# Check for Node.js
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Host "ERROR: Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

$nodeVersion = node --version
Write-Host "Found: Node.js $nodeVersion" -ForegroundColor Green
Write-Host ""

# Install backend dependencies
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
Push-Location backend
try {
    uv sync
    Write-Host "Backend dependencies installed!" -ForegroundColor Green
} finally {
    Pop-Location
}
Write-Host ""

# Install frontend dependencies and build
Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
Push-Location frontend
try {
    npm install
    Write-Host "Frontend dependencies installed!" -ForegroundColor Green
    
    Write-Host "Building frontend for production..." -ForegroundColor Yellow
    npm run build
    Write-Host "Frontend built successfully!" -ForegroundColor Green
} finally {
    Pop-Location
}

# Copy build output to backend
Write-Host "Copying frontend to backend..." -ForegroundColor Yellow
$frontendOut = "frontend\out"
$backendDist = "backend\frontend_dist"
if (Test-Path $backendDist) {
    Remove-Item -Recurse -Force $backendDist
}
Copy-Item -Recurse -Force $frontendOut $backendDist
Write-Host "Frontend copied to $backendDist" -ForegroundColor Green

# Verify frontend_dist was created
$fileCount = (Get-ChildItem $backendDist -Recurse -File).Count
Write-Host "Static frontend files: $fileCount files in $backendDist" -ForegroundColor Green
Write-Host ""

# Add to startup if requested
if ($WithStartup) {
    Write-Host ""
    Write-Host "Setting up Windows startup..." -ForegroundColor Yellow
    
    $startupFolder = [Environment]::GetFolderPath('Startup')
    $shortcutPath = Join-Path $startupFolder "ProjectDashboard.lnk"
    $targetPath = Join-Path $PSScriptRoot "run_tray.pyw"
    
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "pythonw.exe"
    $shortcut.Arguments = "`"$targetPath`""
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Description = "Project Dashboard System Tray"
    $shortcut.Save()
    
    Write-Host "Startup shortcut created at: $shortcutPath" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Setup Complete! ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the dashboard:" -ForegroundColor White
Write-Host "  Option 1: Double-click 'run_tray.pyw' (background, system tray)" -ForegroundColor Gray
Write-Host "  Option 2: Run manually:" -ForegroundColor Gray
Write-Host "            cd backend && uv run uvicorn backend.main:app --port 37453" -ForegroundColor Gray
Write-Host ""
Write-Host "Dashboard URL: http://localhost:37453" -ForegroundColor Cyan

if (-not $BuildOnly) {
    Write-Host ""
    $launch = Read-Host "Launch dashboard now? (Y/n)"
    if ($launch -ne 'n' -and $launch -ne 'N') {
        Write-Host "Starting dashboard..." -ForegroundColor Yellow
        Start-Process pythonw.exe -ArgumentList "`"$PSScriptRoot\run_tray.pyw`"" -WorkingDirectory $PSScriptRoot
        Start-Sleep -Seconds 2
        Start-Process "http://localhost:37453"
    }
}
