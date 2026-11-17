import sqlite3

conn = sqlite3.connect('storage/patrol.db')
c = conn.cursor()

# 1. Update reports table
updated_source = c.execute("UPDATE reports SET source_channel = 'BROWSER_EXTENSION' WHERE source_channel LIKE '%TELEGRAM%'").rowcount
updated_rep_id = c.execute("UPDATE reports SET reporter_identifier = 'Analyst-Extension' WHERE reporter_identifier IS NULL OR reporter_identifier = '' OR reporter_identifier LIKE '%Telegram%'").rowcount
updated_tele_id = c.execute("UPDATE reports SET reporter_telegram_id = 0, reviewer_telegram_id = 0 WHERE reporter_telegram_id != 0 OR reviewer_telegram_id != 0").rowcount

# 2. Check if patrol_users table exists and clean it
try:
    c.execute("UPDATE patrol_users SET username = 'analyst_extension' WHERE username LIKE '%telegram%'")
except Exception:
    pass

# 3. Check audit_logs table
try:
    c.execute("UPDATE audit_logs SET actor_telegram_id = 0 WHERE actor_telegram_id != 0")
    c.execute("UPDATE audit_logs SET actor_username = 'Analyst-Extension' WHERE actor_username LIKE '%Telegram%'")
except Exception:
    pass

conn.commit()
print(f"Cleaned database: {updated_source} reports source_channel updated, {updated_rep_id} reporter_identifier updated, {updated_tele_id} telegram_ids reset.")
conn.close()
