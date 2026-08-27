import os
import sqlite3
import json

def inspect_database():
    db_path = "app.db"
    if not os.path.exists(db_path):
        print("Database file 'app.db' does not exist yet. Initializing...")
        from app.seed.seed import seed_data
        seed_data()
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 60)
    print("CAREAUTH AI -- DATABASE SCHEMA & DATA REPORT")
    print("=" * 60)
    print(f"File Path: {os.path.abspath(db_path)}")
    print(f"File Size: {os.path.getsize(db_path):,} bytes\n")
    
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;").fetchall()
    
    for (t_name,) in tables:
        count = cursor.execute(f"SELECT COUNT(*) FROM {t_name}").fetchone()[0]
        cols = cursor.execute(f"PRAGMA table_info({t_name})").fetchall()
        col_names = [f"{c[1]} ({c[2]})" for c in cols]
        
        print(f"TABLE: [{t_name}] ({count} records)")
        print(f"   Columns: {', '.join(col_names)}")
        
        # Show sample row if exists
        sample = cursor.execute(f"SELECT * FROM {t_name} LIMIT 1").fetchone()
        if sample:
            sample_dict = dict(zip([c[1] for c in cols], sample))
            # Format preview nicely
            preview = json.dumps(sample_dict, default=str)
            if len(preview) > 120:
                preview = preview[:117] + "..."
            print(f"   Sample: {preview}")
        print("-" * 60)

if __name__ == "__main__":
    inspect_database()
