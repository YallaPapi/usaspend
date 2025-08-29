#!/usr/bin/env python3

import sqlite3
import os

print("=== DEBUG DATABASE TEST ===")

# Check if database exists
db_path = "data/app.db"
if os.path.exists(db_path):
    print(f"Database exists at: {db_path}")
else:
    print("Database does not exist!")
    exit(1)

# Connect and read data
try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("\n=== INGEST RUNS ===")
    cur.execute('SELECT source, status, records_fetched, records_normalized FROM ingest_runs ORDER BY id DESC LIMIT 3')
    runs = cur.fetchall()
    if runs:
        for run in runs:
            print(f"  {run[0]} - {run[1]} - fetched: {run[2]}, normalized: {run[3]}")
    else:
        print("  No run records found")

    print("\n=== FULL RUN DETAILS (including errors) ===")
    cur.execute('SELECT source, status, records_fetched, records_normalized, errors FROM ingest_runs ORDER BY id DESC LIMIT 3')
    full_runs = cur.fetchall()
    for i, run in enumerate(full_runs):
        print(f"Run {i+1}: {run[0]}")
        print(f"  Status: {run[1]}")
        print(f"  Fetched: {run[2]}, Normalized: {run[3]}")
        if run[4]:
            print(f"  ERROR: {run[4]}")
        else:
            print("  ERROR: None")
        print()

    print("\n=== COMPANIES ===")
    cur.execute('SELECT COUNT(*) FROM companies')
    company_count = cur.fetchone()[0]
    print(f"  Total companies: {company_count}")

    if company_count > 0:
        cur.execute('SELECT name, country FROM companies LIMIT 3')
        companies = cur.fetchall()
        for company in companies:
            print(f"  - {company[0]} ({company[1]})")

    print("\n=== FUNDING EVENTS ===")
    cur.execute('SELECT COUNT(*) FROM funding_events')
    event_count = cur.fetchone()[0]
    print(f"  Total events: {event_count}")

    if event_count > 0:
        cur.execute('''
            SELECT c.name, e.funding_type, e.amount, e.source, e.date
            FROM companies c
            JOIN funding_events e ON e.company_id = c.id
            ORDER BY e.id DESC
            LIMIT 5
        ''')
        events = cur.fetchall()
        for event in events:
            amount = f"${event[2]}" if event[2] else "No amount"
            print(f"  - {event[0]}: {event[1]} {amount} from {event[3]} on {event[4]}")

    conn.close()

except Exception as e:
    print(f"Error reading database: {e}")
    import traceback
    traceback.print_exc()

print("\n=== SYSTEM CHECK ===")
print(f"Python version: {os.sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Files in current directory: {os.listdir('.')}")
if os.path.exists("src"):
    print(f"SRC directory contents: {os.listdir('src')}")