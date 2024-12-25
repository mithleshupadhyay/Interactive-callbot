import sqlite3

conn = sqlite3.connect('callbot.db')
c = conn.cursor()

# Create table
c.execute('''
CREATE TABLE IF NOT EXISTS call_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    contact_number TEXT NOT NULL,
    interested_in_home_loan TEXT,
    time_period_of_loan TEXT,
    location_of_home TEXT,
    any_other_home_loan TEXT,
    # transcript TEXT
)
''')

conn.commit()
conn.close()