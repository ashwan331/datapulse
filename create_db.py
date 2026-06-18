import sqlite3

conn = sqlite3.connect("database/company.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product TEXT,
    region TEXT,
    sales INTEGER,
    profit INTEGER
)
""")

data = [
    ("Laptop","North",50000,10000),
    ("Mobile","South",30000,5000),
    ("Tablet","East",25000,4000),
    ("Laptop","West",60000,12000),
    ("Mobile","North",45000,7000)
]

cursor.executemany(
    "INSERT INTO sales(product,region,sales,profit) VALUES(?,?,?,?)",
    data
)

conn.commit()
conn.close()

print("Database Created Successfully")