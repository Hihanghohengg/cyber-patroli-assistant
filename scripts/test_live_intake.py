import requests
import json
import time

url = "http://127.0.0.1:8000/api/v1/assistant/intake"
payload = {
    "url": "https://www.youtube.com/watch?v=70wSZypQJZY",
    "source_channel": "BROWSER_EXTENSION",
    "reporter_identifier": "Analyst-Browser",
    "title": "Beli Semua Samba ver. Lokal - Mana yang Terbaik?",
    "caption": "Gw ngebahas hampir semua sepatu lokal yang menurut gw punya looks ala sepatu samba. Dari yang harganya 200 ribuan sampe yang paling mahal.",
    "username": "shoesreview_id",
    "display_name": "Review Sepatu Lokal",
    "views_count": 45000,
    "likes_count": 1250,
    "comments_count": 320,
}

print("Submitting live intake request to", url)
t0 = time.time()
resp = requests.post(url, json=payload, timeout=60)
elapsed = time.time() - t0
print(f"Response status: {resp.status_code} ({elapsed:.2f}s)")
if resp.status_code == 200:
    data = resp.json()
    print("Ticket:", data.get("ticket_number"))
    print("AI Status:", data.get("ai_status"))
    print("AI Predicted Label:", data.get("ai_predicted_label"))
    print("AI Confidence:", data.get("ai_confidence_score"))
    print("AI Summary:", data.get("ai_summary"))
    print("\nSUCCESS!")
else:
    print("Error:", resp.text)
