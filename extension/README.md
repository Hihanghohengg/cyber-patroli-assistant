# Cyber Patrol Assistant — Browser Agent (Chrome & Edge Extension)

Ekstensi peramban resmi untuk **Sistem Asisten Patroli Siber & Intelijen Sosial**.

## Fitur Utama
1. **Auto-Detection Tab Aktif**: Mendeteksi otomatis tautan postingan publik dari **TikTok**, **YouTube**, **Instagram**, dan **X (Twitter)** saat analis berselancar di media sosial.
2. **1-Click AI Triage**: Mengirim URL dan metadata ke backend FastAPI (`http://localhost:8000/api/v1/assistant/intake`) untuk triase instan multimodal 5W+1H dan pencarian preseden RAG.
3. **Floating In-Page Badge**: Tombol mengambang di pojok kanan bawah halaman media sosial untuk pelaporan cepat tanpa harus membuka popup.
4. **Context Menu (Klik Kanan)**: Klik kanan pada tautan apa pun dan pilih *"🛡️ Kirim Tautan ke Cyber Patrol Assistant"* untuk mendaftarkan tiket patroli otomatis.

---

## Cara Pemasangan di Google Chrome / Microsoft Edge

1. Buka browser **Google Chrome** atau **Microsoft Edge**.
2. Ketik pada address bar:
   - Chrome: `chrome://extensions`
   - Edge: `edge://extensions`
3. Aktifkan **"Developer mode"** (Mode Pengembang) di pojok kanan atas.
4. Klik tombol **"Load unpacked"** (Muat yang belum dibongkar).
5. Pilih folder:
   ```
   d:\Obed\mini project\cyber-patrol-assistant\extension
   ```
6. Ekstensi **"Cyber Patrol Assistant — Browser Agent"** akan langsung aktif di browser Anda!
7. Klik ikon ekstensi di toolbar browser saat berada di halaman video TikTok/YouTube untuk langsung menguji triase AI satu kali klik.
