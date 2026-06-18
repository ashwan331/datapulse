from flask import Flask, render_template, request, redirect, session, send_file
import sqlite3
import pandas as pd
import os
from reportlab.pdfgen import canvas

app = Flask(__name__)

app.secret_key = "datapulse_secret"

UPLOAD_FOLDER = "uploads"
DATABASE = "database/company.db"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists("database"):
    os.makedirs("database")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == "admin" and password == "admin123":

            session["user"] = username

            return redirect("/")

    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


@app.route("/download_excel")
def download_excel():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)

    df = pd.read_sql(
        "SELECT * FROM sales",
        conn
    )

    conn.close()

    filename = "sales_report.xlsx"

    df.to_excel(
        filename,
        index=False
    )

    return send_file(
        filename,
        as_attachment=True
    )


@app.route("/download_pdf")
def download_pdf():

    if "user" not in session:
        return redirect("/login")

    conn = sqlite3.connect(DATABASE)

    df = pd.read_sql(
        "SELECT * FROM sales",
        conn
    )

    conn.close()

    filename = "sales_report.pdf"

    c = canvas.Canvas(filename)

    c.drawString(
        100,
        800,
        "DataPulse Analytics Report"
    )

    y = 760

    for index, row in df.iterrows():

        text = (
            f"{row['product']} | "
            f"{row['region']} | "
            f"{row['sales']} | "
            f"{row['profit']}"
        )

        c.drawString(
            50,
            y,
            text
        )

        y -= 20

        if y < 50:
            c.showPage()
            y = 800

    c.save()

    return send_file(
        filename,
        as_attachment=True
    )


@app.route("/", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        file = request.files.get("file")

        if file and file.filename != "":

            filepath = os.path.join(
                UPLOAD_FOLDER,
                file.filename
            )

            file.save(filepath)

            df = pd.read_csv(filepath)

            df.columns = df.columns.str.lower()

            conn = sqlite3.connect(DATABASE)

            df.to_sql(
                "sales",
                conn,
                if_exists="replace",
                index=False
            )

            conn.close()

            return redirect("/")

    try:

        conn = sqlite3.connect(DATABASE)

        df = pd.read_sql(
            "SELECT * FROM sales",
            conn
        )

        conn.close()

    except:

        df = pd.DataFrame(
            columns=[
                "product",
                "region",
                "sales",
                "profit"
            ]
        )

    if len(df) > 0:

        df.columns = df.columns.str.lower()

        region_filter = request.args.get(
            "region",
            "All"
        )

        product_filter = request.args.get(
            "product",
            "All"
        )

        search = request.args.get(
            "search",
            ""
        )

        if region_filter != "All":
            df = df[
                df["region"] == region_filter
            ]

        if product_filter != "All":
            df = df[
                df["product"] == product_filter
            ]

        if search:
            df = df[
                df["product"].astype(str).str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

        total_sales = (
            df["sales"].sum()
            if len(df) > 0 else 0
        )

        total_profit = (
            df["profit"].sum()
            if len(df) > 0 else 0
        )

        total_orders = len(df)

        regions = sorted(
            df["region"].unique()
        ) if len(df) > 0 else []

        products = sorted(
            df["product"].unique()
        ) if len(df) > 0 else []

        region_data = (
            df.groupby("region")["sales"]
            .sum()
            .reset_index()
        ) if len(df) > 0 else pd.DataFrame()

        product_data = (
            df.groupby("product")["sales"]
            .sum()
            .reset_index()
        ) if len(df) > 0 else pd.DataFrame()

        if len(df) > 0:

            best_product = (
                df.groupby("product")["sales"]
                .sum()
                .idxmax()
            )

            best_region = (
                df.groupby("region")["sales"]
                .sum()
                .idxmax()
            )

        else:

            best_product = "No Data"
            best_region = "No Data"

    else:

        total_sales = 0
        total_profit = 0
        total_orders = 0

        regions = []
        products = []

        best_product = "No Data"
        best_region = "No Data"

        region_data = pd.DataFrame()
        product_data = pd.DataFrame()

        search = ""

    return render_template(
        "dashboard.html",
        sales=total_sales,
        profit=total_profit,
        orders=total_orders,
        best_product=best_product,
        best_region=best_region,
        regions=regions,
        products=products,
        search=search,
        region_labels=region_data["region"].tolist()
        if len(region_data) > 0 else [],
        region_values=region_data["sales"].tolist()
        if len(region_data) > 0 else [],
        product_labels=product_data["product"].tolist()
        if len(product_data) > 0 else [],
        product_values=product_data["sales"].tolist()
        if len(product_data) > 0 else [],
        table_data=df.to_dict(orient="records")
    )


if __name__ == "__main__":
    app.run(debug=True)