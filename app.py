from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

@app.route("/")
def dashboard():

    conn = sqlite3.connect("database/company.db")
    cursor = conn.cursor()

    cursor.execute("SELECT SUM(sales) FROM sales")
    total_sales = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(profit) FROM sales")
    total_profit = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        sales=total_sales,
        profit=total_profit
    )

if __name__ == "__main__":
    app.run(debug=True)