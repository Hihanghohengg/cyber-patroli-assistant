# TILIK v5.0 — PowerShell Setup Script
$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "       [+] SETUP INSTAN TILIK v5.0 (ASISTEN PATROLI SIBER TERPADU)" -ForegroundColor Cyan
Write-Host "===============================================================================" -ForegroundColor Cyan

# 1. Cek Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python tidak ditemukan di PATH. Silakan pasang Python 3.11+." -ForegroundColor Red
    exit 1
}

# 2. Venv
if (-not (Test-Path "venv\Scripts\python.exe")) {
    Write-Host "[*] Membuat virtual environment Python (venv)..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "[v] Virtual environment berhasil dibuat." -ForegroundColor Green
} else {
    Write-Host "[v] Virtual environment sudah tersedia." -ForegroundColor Green
}

# 3. Pip dependencies
Write-Host "[*] Memperbarui pip dan memasang paket..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -m pip install --upgrade pip
& "venv\Scripts\python.exe" -m pip install -r requirements.txt

# 4. Playwright Chromium
Write-Host "[*] Memeriksa instalasi Playwright Chromium..." -ForegroundColor Yellow
& "venv\Scripts\python.exe" -m playwright install chromium

# 5. Folder Storage
New-Item -ItemType Directory -Force -Path "storage\evidences" | Out-Null
New-Item -ItemType Directory -Force -Path "storage\reports" | Out-Null
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[v] File .env diinisialisasi dari .env.example." -ForegroundColor Green
    }
}

# 6. Ollama Check
Write-Host "[*] Memeriksa status Ollama lokal..." -ForegroundColor Yellow
try {
    $res = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[v] Ollama aktif di http://127.0.0.1:11434" -ForegroundColor Green
    Write-Host "[*] Pastikan model tersedia: ollama pull qwen2.5:7b && ollama pull bge-m3" -ForegroundColor Cyan
} catch {
    Write-Host "[WARN] Layanan Ollama tidak merespon di http://127.0.0.1:11434 (Pastikan Ollama dijalankan)." -ForegroundColor Yellow
}

Write-Host "===============================================================================" -ForegroundColor Cyan
Write-Host "[v] Setup selesai. Jalankan sistem menggunakan .\run.ps1" -ForegroundColor Green
Write-Host "===============================================================================" -ForegroundColor Cyan
