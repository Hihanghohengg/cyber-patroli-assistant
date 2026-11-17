@echo off
setlocal enabledelayedexpansion
title TILIK v5.0 — Setup Instan Lingkungan Lokal
cd /d "%~dp0"

echo ===============================================================================
echo        [+] SETUP INSTAN TILIK v5.0 - ASISTEN PATROLI SIBER TERPADU
echo ===============================================================================

:: 1. Cek Python
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan di PATH sistem. Silakan install Python 3.11+.
    pause
    exit /b 1
)

:: 2. Setup Venv
if not exist "venv\Scripts\python.exe" (
    echo [*] Membuat virtual environment Python [venv]...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Gagal membuat venv.
        pause
        exit /b 1
    )
    echo [v] Virtual environment berhasil dibuat.
) else (
    echo [v] Virtual environment sudah tersedia.
)

:: 3. Install Dependensi
echo [*] Memperbarui pip dan menginstal dependensi requirements.txt...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [WARN] Beberapa paket mungkin gagal diinstal via pip jika offline.
)

:: 4. Install Playwright Chromium Headless
echo [*] Memeriksa browser Playwright Chromium...
"venv\Scripts\python.exe" -m playwright install chromium
if errorlevel 1 (
    echo [WARN] Playwright chromium belum terinstal atau butuh koneksi internet.
)

:: 5. Buat direktori penyimpanan lokal
if not exist "storage\evidences" mkdir "storage\evidences"
if not exist "storage\reports" mkdir "storage\reports"
if not exist ".env" (
    if exist ".env.example" (
        echo [*] Menyalin .env.example menjadi .env...
        copy ".env.example" ".env" >nul
    )
)

:: 6. Periksa Ketersediaan Ollama
echo [*] Memeriksa status Ollama lokal [http://127.0.0.1:11434]...
curl -s http://127.0.0.1:11434/api/tags >nul 2>nul
if not errorlevel 1 (
    echo [v] Layanan Ollama aktif.
    echo [*] Disarankan memastikan model berikut tersedia:
    echo     - ollama pull qwen2.5:7b
    echo     - ollama pull bge-m3
) else (
    echo [WARN] Ollama belum aktif di http://127.0.0.1:11434.
    echo        Pastikan Ollama terinstal dan berjalan sebelum inferensi AI.
)

echo ===============================================================================
echo [v] Setup Selesai! Jalankan sistem dengan: run.bat
echo ===============================================================================
pause
