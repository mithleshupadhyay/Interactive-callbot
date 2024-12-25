import sqlite3

def view_database():
    conn = sqlite3.connect('callbot.db')
    c = conn.cursor()

    # Retrieve data from the call_details table
    c.execute('SELECT * FROM call_details')
    rows = c.fetchall()

    if not rows:
        print("No data found in the call_details table.")
    else:
        # Print the data
        for row in rows:
            print(f"ID: {row[0]}")
            print(f"Name: {row[1]}")
            print(f"Contact Number: {row[2]}")
            print(f"Interested in Home Loan: {row[3]}")
            print(f"Time Period of Loan: {row[4]}")
            print(f"Location of Home: {row[5]}")
            print(f"Any Other Home Loan: {row[6]}")
            print(f"Transcript: {row[7]}")
            print("-" * 40)

    conn.close()

if __name__ == "__main__":
    view_database()