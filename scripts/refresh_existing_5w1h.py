import sqlite3
from app.services.intelligence.analysis_5w1h import Analysis5W1HService, format_indonesian_date

conn = sqlite3.connect('storage/patrol.db')
c = conn.cursor()

service = Analysis5W1HService()

rows = c.execute('''
    SELECT ca.analysis_id, ca.content_id, c.title, c.caption_text, c.platform, c.canonical_url,
           a.username, a.display_name, c.posted_at, c.metadata
    FROM content_analyses ca
    JOIN contents c ON ca.content_id = c.content_id
    LEFT JOIN accounts a ON c.account_id = a.account_id
''').fetchall()

print(f"Refreshing 5W+1H for {len(rows)} content analysis rows...")
updated_count = 0
for row in rows:
    analysis_id, content_id, title, caption, platform, canonical_url, username, display_name, posted_at, extra_meta_str = row
    transcript = ""
    if extra_meta_str:
        import json
        try:
            em = json.loads(extra_meta_str) if isinstance(extra_meta_str, str) else extra_meta_str
            if isinstance(em, dict):
                transcript = em.get("transcript", "")
        except Exception:
            pass

    # Extract clean heuristic 5w1h
    h = service._heuristic_fallback(
        text=caption or "",
        title=title or "",
        author=username or "",
        display_name=display_name or "",
        platform=platform or "youtube",
        canonical_url=canonical_url or "",
        posted_at=posted_at,
        transcript=transcript,
        caption=caption or "",
    )

    c.execute('''
        UPDATE content_analyses
        SET what = ?, who = ?, when_info = ?, where_info = ?, why = ?, how = ?
        WHERE analysis_id = ?
    ''', (h.what, h.who, h.when_info, h.where_info, h.why, h.how, analysis_id))
    updated_count += 1

conn.commit()
print(f"Successfully refreshed {updated_count} 5W+1H entries in database!")

# Verify a sample
sample = c.execute('SELECT what, who, when_info, where_info, why, how FROM content_analyses LIMIT 3').fetchall()
for idx, s in enumerate(sample):
    print(f"\n--- Sample {idx+1} ---")
    print("WHAT :", s[0][:60])
    print("WHO  :", s[1])
    print("WHEN :", s[2])
    print("WHERE:", s[3][:60])
    print("WHY  :", s[4][:80])
    print("HOW  :", s[5][:80])

conn.close()
