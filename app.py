from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    send_file
)

import sqlite3
import pandas as pd
import os
from io import BytesIO

from reportlab.pdfgen import canvas
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename


# ==================================================
# APP CONFIG
# ==================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "datapulse_secret"
)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

UPLOAD_FOLDER = "uploads"
DATABASE = "database/company.db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs("database", exist_ok=True)


# ==================================================
# DATABASE SETUP
# ==================================================

def get_db():
    return sqlite3.connect(DATABASE)


with get_db() as conn:

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    conn.commit()


# ==================================================
# SIGNUP
# ==================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        hashed_password = generate_password_hash(
            password
        )

        try:

            with get_db() as conn:

                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT INTO users
                    (
                        name,
                        email,
                        password
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        name,
                        email,
                        hashed_password
                    )
                )

                conn.commit()

            return redirect("/login")

        except sqlite3.IntegrityError:

            return "Email already registered"

    return render_template(
        "signup.html"
    )

@app.route("/home")
def home():

    return render_template(
        "index.html"
    )
# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        print("LOGIN ATTEMPT")
        print("Email:", email)

        conn = sqlite3.connect(DATABASE)

        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        )

        user = cursor.fetchone()

        conn.close()

        print("User:", user)

        if user:

            if check_password_hash(user[3], password):

                print("PASSWORD CORRECT")

                session["user"] = {
                    "name": user[1],
                    "email": user[2]
                }

                return redirect("/")

            else:

                print("WRONG PASSWORD")

        else:

            print("USER NOT FOUND")

    return render_template("login.html")
# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/", methods=["GET", "POST"])
def dashboard():

    if "user" not in session:
        return redirect("/home")

    # ----------------------------------------------
    # FILE UPLOAD
    # ----------------------------------------------

    if request.method == "POST":

        file = request.files.get("file")

        if file and file.filename:

            filename = secure_filename(
                file.filename
            )

            filepath = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            file.save(filepath)

            try:

                df = pd.read_csv(filepath)

                df.columns = (
                    df.columns
                    .str.strip()
                    .str.lower()
                )

                required_columns = {
                    "product",
                    "region",
                    "sales",
                    "profit"
                }

                if not required_columns.issubset(
                    df.columns
                ):
                    return (
                        "CSV must contain "
                        "product, region, sales, profit"
                    )

                df["sales"] = pd.to_numeric(
                    df["sales"],
                    errors="coerce"
                )

                df["profit"] = pd.to_numeric(
                    df["profit"],
                    errors="coerce"
                )

                df = df.dropna(
                    subset=[
                        "sales",
                        "profit"
                    ]
                )

                with get_db() as conn:

                    df.to_sql(
                        "sales",
                        conn,
                        if_exists="replace",
                        index=False
                    )

                return redirect("/")

            except Exception as e:

                return f"Upload Error: {e}"

    # ----------------------------------------------
    # LOAD SALES DATA
    # ----------------------------------------------

    try:

        with get_db() as conn:

            df = pd.read_sql(
                "SELECT * FROM sales",
                conn
            )

    except Exception:

        df = pd.DataFrame(
            columns=[
                "product",
                "region",
                "sales",
                "profit"
            ]
        )

    # ----------------------------------------------
    # FILTERS
    # ----------------------------------------------

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

    if not df.empty:

        df.columns = (
            df.columns
            .str.strip()
            .str.lower()
        )

        if region_filter != "All":

            df = df[
                df["region"]
                .astype(str)
                .str.lower()
                ==
                region_filter.lower()
            ]

        if product_filter != "All":

            df = df[
                df["product"]
                .astype(str)
                .str.lower()
                ==
                product_filter.lower()
            ]

        if search:

            df = df[
                df["product"]
                .astype(str)
                .str.contains(
                    search,
                    case=False,
                    na=False
                )
            ]

    has_data = not df.empty

    # ----------------------------------------------
    # KPIs
    # ----------------------------------------------

    total_sales = (
        float(df["sales"].sum())
        if has_data else 0
    )

    total_profit = (
        float(df["profit"].sum())
        if has_data else 0
    )

    total_orders = (
        len(df)
        if has_data else 0
    )

    avg_sales = (
        round(df["sales"].mean(), 2)
        if has_data else 0
    )

    avg_profit = (
        round(df["profit"].mean(), 2)
        if has_data else 0
    )

    max_sales = (
        float(df["sales"].max())
        if has_data else 0
    )

    min_sales = (
        float(df["sales"].min())
        if has_data else 0
    )

    regions = (
        sorted(
            df["region"]
            .astype(str)
            .unique()
        )
        if has_data else []
    )

    products = (
        sorted(
            df["product"]
            .astype(str)
            .unique()
        )
        if has_data else []
    )

    # ----------------------------------------------
    # CHART DATA
    # ----------------------------------------------

    if has_data:

        region_data = (
            df.groupby("region")["sales"]
            .sum()
            .reset_index()
        )

        product_data = (
            df.groupby("product")["sales"]
            .sum()
            .reset_index()
        )

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

        region_data = pd.DataFrame()
        product_data = pd.DataFrame()

        best_product = "No Data"
        best_region = "No Data"

    # ----------------------------------------------
    # RENDER
    # ----------------------------------------------

    return render_template(
        "dashboard.html",

        sales=total_sales,
        profit=total_profit,
        orders=total_orders,

        avg_sales=avg_sales,
        avg_profit=avg_profit,

        max_sales=max_sales,
        min_sales=min_sales,

        best_product=best_product,
        best_region=best_region,

        regions=regions,
        products=products,

        selected_region=region_filter,
        selected_product=product_filter,

        search=search,

        region_labels=(
            region_data["region"].tolist()
            if not region_data.empty
            else []
        ),

        region_values=(
            region_data["sales"].tolist()
            if not region_data.empty
            else []
        ),

        product_labels=(
            product_data["product"].tolist()
            if not product_data.empty
            else []
        ),

        product_values=(
            product_data["sales"].tolist()
            if not product_data.empty
            else []
        ),

        table_data=df.to_dict(
            orient="records"
        )
    )


# ==================================================
# EXCEL EXPORT
# ==================================================

@app.route("/download_excel")
def download_excel():

    if "user" not in session:
        return redirect("/login")

    try:

        with get_db() as conn:

            df = pd.read_sql(
                "SELECT * FROM sales",
                conn
            )

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            df.to_excel(
                writer,
                index=False,
                sheet_name="Sales"
            )

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="sales_report.xlsx",
            mimetype=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )
        )

    except Exception as e:

        return f"Export Error: {e}"


# ==================================================
# PDF EXPORT
# ==================================================

@app.route("/download_pdf")
def download_pdf():

    if "user" not in session:
        return redirect("/login")

    try:

        with get_db() as conn:

            df = pd.read_sql(
                "SELECT * FROM sales",
                conn
            )

        buffer = BytesIO()

        pdf = canvas.Canvas(buffer)

        pdf.drawString(
            180,
            800,
            "DataPulse Analytics Report"
        )

        y = 760

        pdf.drawString(
            40,
            y,
            "Product"
        )

        pdf.drawString(
            200,
            y,
            "Region"
        )

        pdf.drawString(
            320,
            y,
            "Sales"
        )

        pdf.drawString(
            430,
            y,
            "Profit"
        )

        y -= 25

        for _, row in df.iterrows():

            pdf.drawString(
                40,
                y,
                str(row["product"])
            )

            pdf.drawString(
                200,
                y,
                str(row["region"])
            )

            pdf.drawString(
                320,
                y,
                str(row["sales"])
            )

            pdf.drawString(
                430,
                y,
                str(row["profit"])
            )

            y -= 20

            if y < 50:

                pdf.showPage()
                y = 800

        pdf.save()

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="sales_report.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:

        return f"PDF Export Error: {e}"


# ==================================================
# RUN APP
# ==================================================

if __name__ == "__main__":
    app.run(debug=True)