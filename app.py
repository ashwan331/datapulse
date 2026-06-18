from flask_mail import Mail, Message
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

from reportlab.pdfgen import canvas

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename


# =====================================
# APP CONFIG
# =====================================

app = Flask(__name__)

app.secret_key = "datapulse_analytics_dashboard_2025_secure"
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True

app.config["MAIL_USERNAME"] = "ashwanyadav6612@gmail.com"
app.config["MAIL_PASSWORD"] = "ashwan@12943"

mail = Mail(app)
UPLOAD_FOLDER = "uploads"
DATABASE = "database/company.db"

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)

os.makedirs(
    "database",
    exist_ok=True
)


# =====================================
# DATABASE
# =====================================

def get_db():

    return sqlite3.connect(
        DATABASE
    )


with get_db() as conn:

    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """
    )

    conn.commit()
app.secret_key = "datapulse_analytics_dashboard_2025_secure"

# =====================================
# HOME
# =====================================

@app.route("/home")
def home():

    return render_template(
        "index.html"
    )


# =====================================
# SIGNUP
# =====================================

@app.route(
    "/signup",
    methods=["GET", "POST"]
)
def signup():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]

        password = generate_password_hash(
            request.form["password"]
        )

        try:

            conn = get_db()

            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password
                )
                VALUES
                (
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    name,
                    email,
                    password
                )
            )

            conn.commit()

            conn.close()

            return redirect(
                "/login"
            )

        except Exception as e:
            print("SIGNUP ERROR:", e)
            return "Email already registered"
        return render_template(
        "signup.html"
    )


# =====================================
# LOGIN
# =====================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE email=?
            """,
            (email,)
        )

        user = cursor.fetchone()

        conn.close()

        if user:

            if check_password_hash(
                user[3],
                password
            ):

                session["user"] = {
                    "name": user[1],
                    "email": user[2]
                }

                return redirect("/")

    return render_template(
        "login.html",
        error="Invalid email or password"
    )
# =====================================
# FORGOT PASSWORD
# =====================================

@app.route(
    "/forgot_password",
    methods=["GET", "POST"]
)
def forgot_password():

    if request.method == "POST":

        email = request.form["email"]

        password = generate_password_hash(
            request.form["password"]
        )

        conn = get_db()

        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE users
            SET password=?
            WHERE email=?
            """,
            (
                password,
                email
            )
        )

        conn.commit()

        conn.close()

        return redirect(
            "/login"
        )

    return render_template(
        "forgot_password.html"
    )


# =====================================
# LOGOUT
# =====================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        "/login"
    )


# =====================================
# PROFILE
# =====================================

@app.route("/profile")
def profile():

    if "user" not in session:

        return redirect(
            "/login"
        )

    return render_template(
        "profile.html",
        user=session["user"]
    )


# =====================================
# ADMIN PANEL
# =====================================

@app.route("/admin")
def admin():

    if "user" not in session:

        return redirect(
            "/login"
        )

    conn = get_db()

    users = pd.read_sql(
        """
        SELECT
        id,
        name,
        email
        FROM users
        """,
        conn
    )

    conn.close()

    return render_template(
        "admin.html",
        users=users.to_dict(
            orient="records"
        ),
        total_users=len(users)
    )


@app.route(
    "/delete_user/<int:user_id>"
)
def delete_user(user_id):

    if "user" not in session:

        return redirect(
            "/login"
        )

    conn = get_db()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM users
        WHERE id=?
        """,
        (user_id,)
    )

    conn.commit()

    conn.close()

    return redirect(
        "/admin"
    )


# =====================================
# DASHBOARD
# =====================================

@app.route(
    "/",
    methods=["GET", "POST"]
)
def dashboard():

    if "user" not in session:

        return redirect(
            "/home"
        )

    # -------------------------
    # FILE UPLOAD
    # -------------------------

    if request.method == "POST":

        file = request.files.get(
            "file"
        )

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

                df = pd.read_csv(
                    filepath
                )

                df.columns = (
                    df.columns
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
                        "product, region, "
                        "sales and profit"
                    )

                df["user_email"] = (
                    session["user"]["email"]
                )

                conn = get_db()

                df.to_sql(
                    "sales",
                    conn,
                    if_exists="append",
                    index=False
                )

                conn.close()

                return redirect("/")

            except Exception as e:
                print("UPLOAD ERROR:", e)
                return f"Upload Error: {e}"
    # -------------------------
    # LOAD DATA
    # -------------------------

    try:

        conn = get_db()

        df = pd.read_sql(
            """
            SELECT *
            FROM sales
            WHERE user_email=?
            """,
            conn,
            params=(
                session["user"]["email"],
            )
        )

        conn.close()

    except Exception as e:
        print("LOAD ERROR:", e)

    df = pd.DataFrame(
        columns=[
            "product",
            "region",
            "sales",
            "profit"
        ]
    )

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
    
        # -------------------------
    # FILTERS
    # -------------------------

    if not df.empty:

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

    # -------------------------
    # KPI CALCULATIONS
    # -------------------------

    if not df.empty:

        total_sales = float(
            df["sales"].sum()
        )

        total_profit = float(
            df["profit"].sum()
        )

        total_orders = len(df)

        avg_sales = round(
            df["sales"].mean(),
            2
        )

        avg_profit = round(
            df["profit"].mean(),
            2
        )

        max_sales = float(
            df["sales"].max()
        )

        min_sales = float(
            df["sales"].min()
        )

        regions = sorted(
            df["region"]
            .astype(str)
            .unique()
        )

        products = sorted(
            df["product"]
            .astype(str)
            .unique()
        )

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
        trend_data = (
            df.groupby("date")["sales"]
            .sum()
            .reset_index()
            )
        
        profit_region_data = (
            df.groupby("region")["profit"]
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
        
        highest_sales = df["sales"].max()
        highest_profit = df["profit"].max()
        insight_1 = f"Best Region: {best_region}"
        insight_2 = f"Best Product: {best_product}"
        insight_3 = f"Highest Sale: ₹{highest_sales:,.0f}"
        insight_4 = f"Highest Profit: ₹{highest_profit:,.0f}"
        top_products = (
            df.groupby("product")["sales"]
            .sum()
            .sort_values(
                ascending=False
                )
                .head(5)
                .reset_index()
                )
        profit_margin = round(
            (total_profit / total_sales) * 100,
            2
            ) if total_sales > 0 else 0
        ai_summary = [
            f"Top performing region is {best_region}.",
            f"Best selling product is {best_product}.",
            f"Profit margin is {profit_margin}%.",
            f"Total orders processed: {total_orders}."
            ]
    else:

        total_sales = 0
        total_profit = 0
        total_orders = 0

        avg_sales = 0
        avg_profit = 0

        max_sales = 0
        min_sales = 0

        regions = []
        products = []

        best_product = "No Data"
        best_region = "No Data"

        region_data = pd.DataFrame()
        product_data = pd.DataFrame()
        profit_region_data = pd.DataFrame()

    # -------------------------
    # RENDER TEMPLATE
    # -------------------------

    return render_template(
        "dashboard.html",
        user=session["user"],
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

        profit_region_labels=(
            profit_region_data["region"].tolist()
            if not profit_region_data.empty
            else []
        ),

        profit_region_values=(
            profit_region_data["profit"].tolist()
            if not profit_region_data.empty
            else []
        ),
        top_products=(
    top_products.to_dict(
        orient="records"
    )
    if not df.empty
    else []
),

trend_labels=(
    trend_data["date"].tolist()
    if not trend_data.empty
    else []
),

trend_values=(
    trend_data["sales"].tolist()
    if not trend_data.empty
    else []
),
insight_1=insight_1,
insight_2=insight_2,
insight_3=insight_3,
insight_4=insight_4,
ai_summary=ai_summary,
table_data=df.to_dict(
    orient="records"
),
    )


# =====================================
# EXCEL EXPORT
# =====================================

@app.route("/download_excel")
def download_excel():

    if "user" not in session:

        return redirect(
            "/login"
        )

    conn = get_db()

    df = pd.read_sql(
        """
        SELECT *
        FROM sales
        WHERE user_email=?
        """,
        conn,
        params=(
            session["user"]["email"],
        )
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


# =====================================
# PDF EXPORT
# =====================================

@app.route("/download_pdf")
def download_pdf():

    if "user" not in session:

        return redirect(
            "/login"
        )

    conn = get_db()

    df = pd.read_sql(
        """
        SELECT *
        FROM sales
        WHERE user_email=?
        """,
        conn,
        params=(
            session["user"]["email"],
        )
    )

    conn.close()

    filename = "sales_report.pdf"

    pdf = canvas.Canvas(
        filename
    )

    pdf.drawString(
        180,
        800,
        "DataPulse Analytics Report"
    )

    y = 760

    for _, row in df.iterrows():

        pdf.drawString(
            40,
            y,
            str(row["product"])
        )

        pdf.drawString(
            180,
            y,
            str(row["region"])
        )

        pdf.drawString(
            320,
            y,
            str(row["sales"])
        )

        pdf.drawString(
            450,
            y,
            str(row["profit"])
        )

        y -= 20

        if y < 50:

            pdf.showPage()
            y = 760

    pdf.save()

    return send_file(
        filename,
        as_attachment=True
    )

@app.route("/send_report")
def send_report():

    if "user" not in session:
        return redirect("/login")

    msg = Message(
        "DataPulse Report",
        sender=app.config["MAIL_USERNAME"],
        recipients=[
            session["user"]["email"]
        ]
    )

    msg.body = """
Your DataPulse report is ready.

Login to view latest analytics.
"""

    mail.send(msg)

    return "Report Sent Successfully"
# =====================================
# RUN APP
# =====================================

if __name__ == "__main__":

    app.run(
        debug=True
    )