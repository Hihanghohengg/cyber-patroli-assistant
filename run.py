"""Launcher Tunggal Sistem Pemantauan Siber (TILIK).

Menjalankan backend API & dashboard dalam satu perintah dan berhenti dengan Ctrl+C.
Usage:
    run.bat
    .\\run.ps1
    python run.py
"""

import argparse
import os
import signal
import subprocess
import sys
import threading
import time
import webbrowser

# Aktifkan encoding UTF-8 agar aman di konsol Windows tanpa UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 1. Pastikan working directory berada pada direktori 'cyber-patrol-assistant'
current_dir = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(current_dir) == "cyber-patrol-assistant":
    base_dir = current_dir
elif os.path.exists(os.path.join(current_dir, "cyber-patrol-assistant")):
    base_dir = os.path.join(current_dir, "cyber-patrol-assistant")
else:
    base_dir = current_dir

os.chdir(base_dir)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# 2. Re-exec dengan Python venv jika dijalankan menggunakan python global
venv_python = os.path.join(base_dir, "venv", "Scripts", "python.exe")
if os.path.exists(venv_python):
    curr_exe = os.path.normcase(os.path.abspath(sys.executable))
    target_exe = os.path.normcase(os.path.abspath(venv_python))
    if curr_exe != target_exe and "--no-reexec" not in sys.argv:
        cmd = [target_exe, os.path.abspath(__file__), "--no-reexec"] + [
            arg for arg in sys.argv[1:] if arg != "--no-reexec"
        ]
        try:
            return_code = subprocess.call(cmd)
            sys.exit(return_code)
        except KeyboardInterrupt:
            sys.exit(0)


def auto_open_browser(url: str, delay: float = 1.5):
    """Buka browser otomatis setelah server menyala."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def kill_process_on_port(port: int):
    """Hentikan proses yang memegang port jika ada proses zombie sebelumnya (Windows)."""
    if sys.platform != "win32":
        return
    try:
        cmd = f"netstat -ano | findstr :{port}"
        output = subprocess.check_output(cmd, shell=True, text=True, errors="ignore")
        for line in output.strip().splitlines():
            parts = line.split()
            if len(parts) >= 5 and "LISTENING" in parts:
                pid = parts[-1]
                if pid and pid != "0" and pid != str(os.getpid()):
                    subprocess.run(
                        f"taskkill /F /PID {pid}",
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
    except Exception:
        pass


def check_and_start_ollama(host: str = "127.0.0.1", port: int = 11434):
    """Periksa konektivitas Ollama di port 11434. Jika belum aktif, coba auto-start di latar belakang."""
    import socket
    import shutil

    def is_port_active(h, p):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                return s.connect_ex((h, p)) == 0
        except Exception:
            return False

    if is_port_active(host, port):
        return True, "TERHUBUNG (Port 11434 Aktif)"

    # Cek ketersediaan binary ollama di sistem
    ollama_cmd = shutil.which("ollama")
    if ollama_cmd:
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)

            subprocess.Popen(
                [ollama_cmd, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            # Tunggu 2-3 detik agar daemon Ollama siap menerima request
            for _ in range(6):
                time.sleep(0.5)
                if is_port_active(host, port):
                    return True, "TERHUBUNG (Auto-Started 'ollama serve')"
        except Exception as err:
            return False, f"Gagal auto-start ({err})"

    return False, "TIDAK AKTIF (Fallback: Local Heuristic)"


def main():
    parser = argparse.ArgumentParser(
        description="Jalankan Sistem Asisten Patroli Siber (FastAPI + Dashboard)."
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port server (default: 8000)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Jangan otomatis membuka browser saat server menyala",
    )
    parser.add_argument("--no-reexec", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    # Bersihkan port dari instance sebelumnya jika ada
    kill_process_on_port(args.port)

    # Pastikan direktori penyimpanan tersedia
    os.makedirs(os.path.join(base_dir, "storage"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "storage", "evidence"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "storage", "reports"), exist_ok=True)

    # Deteksi profil hardware
    gpu_info = "CPU / Integrated Graphics"
    if sys.platform == "win32":
        try:
            ps_cmd = 'powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"'
            ps_out = subprocess.check_output(
                ps_cmd, shell=True, text=True, errors="ignore", stderr=subprocess.DEVNULL
            )
            gpus = [line.strip() for line in ps_out.splitlines() if line.strip() and "name" not in line.lower()]
            if gpus:
                gpu_info = ", ".join(gpus)
        except Exception:
            pass

    # Periksa dan auto-start Ollama jika belum aktif
    ollama_ok, ollama_status = check_and_start_ollama()

    from app.config import settings

    extension_dir = os.path.join(base_dir, "extension")
    dashboard_url = f"http://{args.host}:{args.port}/dashboard/"
    docs_url = f"http://{args.host}:{args.port}/docs"

    banner = f"""
===============================================================================
       [+] SISTEM PEMANTAUAN SIBER TERPADU (TILIK)
===============================================================================
  * Hardware Profile : {gpu_info}
  * Ollama Service   : {ollama_status}
  * Ollama LLM Model : {settings.OLLAMA_MODEL} (Concurrency: {settings.AI_CONCURRENCY})
  * Embedding Model  : {settings.EMBEDDING_MODEL} (Cross-Lingual)
  * OCR Engine       : {settings.OCR_ENGINE.upper()}
  * Dashboard Web    : {dashboard_url}
  * Dokumentasi API  : {docs_url}
  * Folder Ekstensi  : {extension_dir}
-------------------------------------------------------------------------------
  [!] CARA MENGHENTIKAN:
      Tekan kombinasi tombol [Ctrl + C] di terminal ini kapan saja.
===============================================================================
"""
    print(banner)

    if not ollama_ok:
        print("  [!] CATATAN: Ollama daemon belum terdeteksi aktif pada port 11434.")
        print("      Jalankan 'ollama serve' di terminal jika ingin analisis ditenagai model LLM.\n")

    if not args.no_browser:
        t = threading.Thread(
            target=auto_open_browser, args=(dashboard_url, 1.5), daemon=True
        )
        t.start()

    try:
        import uvicorn
        # Jalankan server uvicorn langsung di proses ini
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=True,
        )
    except KeyboardInterrupt:
        print("\n" + "=" * 79)
        print("  [*] Menghentikan Sistem Asisten Patroli Siber...")
        print("  [v] Server dan koneksi database telah ditutup secara aman.")
        print("  [*] Sampai jumpa kembali!")
        print("=" * 79 + "\n")
        sys.exit(0)
    except Exception as ex:
        print(f"\n[ERROR] Gagal menjalankan server: {ex}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
