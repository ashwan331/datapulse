import sqlite3

conn = sqlite3.connect("database/company.db")

cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS sales")

conn.commit()

conn.close()

print("sales table deleted")