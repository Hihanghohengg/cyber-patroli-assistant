import sqlite3
import json

conn = sqlite3.connect('storage/patrol.db')
cursor = conn.cursor()

print("Checking tables for invalid JSON...")
tables = [row[0] for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
json_cols = [
    ('contents', 'metadata'),
    ('reports', 'ai_reasoning'),
    ('reports', 'ai_output'),
    ('content_analysis_5w1h', 'parties_involved'),
    ('content_analysis_5w1h', 'evidence_snippets'),
    ('topic_clusters', 'top_keywords'),
    ('topic_clusters', 'sentiment_distribution'),
    ('topic_clusters', 'risk_distribution'),
    ('trending_topics', 'top_entities'),
    ('trending_topics', 'sentiment_distribution'),
    ('rag_knowledge_chunks', 'metadata'),
    ('entity_cross_references', 'source_context'),
    ('audit_logs', 'details'),
]

for table, col in json_cols:
    try:
        # Check if table and col exist
        rows = cursor.execute(f'SELECT rowid, "{col}" FROM "{table}" WHERE "{col}" IS NOT NULL').fetchall()
        bad_count = 0
        for rowid, val in rows:
            if isinstance(val, str):
                if val.strip() == "":
                    cursor.execute(f'UPDATE "{table}" SET "{col}" = NULL WHERE rowid = ?', (rowid,))
                    bad_count += 1
                else:
                    try:
                        json.loads(val)
                    except Exception as err:
                        print(f"Invalid JSON in {table}.{col} (rowid {rowid}): {val!r} -> {err}")
                        cursor.execute(f'UPDATE "{table}" SET "{col}" = NULL WHERE rowid = ?', (rowid,))
                        bad_count += 1
        if bad_count > 0:
            print(f"Fixed {bad_count} bad JSON entries in {table}.{col}")
    except Exception as e:
        # table might not exist
        pass

conn.commit()
conn.close()
print("Done fixing invalid JSON entries.")
