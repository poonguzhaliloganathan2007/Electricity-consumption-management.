"""
electricity_analysis.py
=======================
Electricity Consumption Management and Energy Usage Analysis System
Data analysis and visualization using Python (Pandas + Matplotlib).

What this script does
---------------------
1. Connects to the MySQL database `electricity_db` (tables: consumers, readings, bills).
2. Retrieves electricity consumption data with one JOIN query.
3. Cleans / preprocesses the data with Pandas (missing and invalid values are handled and logged).
4. Calculates monthly consumption, consumer-wise consumption and high-consumption consumers.
5. Draws six Matplotlib charts and saves them in the `visualizations` folder.
6. Saves the processed data and a text summary report in the `output` folder.

Database settings (nothing sensitive is stored in this file)
------------------------------------------------------------
Set these environment variables before running (Windows PowerShell example):
    $env:DB_HOST = "localhost"
    $env:DB_PORT = "3306"
    $env:DB_USER = "root"
    $env:DB_PASSWORD = "<your-mysql-password>"
    $env:DB_NAME = "electricity_db"
If DB_PASSWORD is not set, the script asks for it at run time.

Usage
-----
    python electricity_analysis.py                 # real data from MySQL
    python electricity_analysis.py --top-n 3       # change the size of the "top consumers" chart
    python electricity_analysis.py --demo          # ILLUSTRATIVE sample data, no database needed
                                                   # (outputs go to a 'sample_illustrative' sub-folder
                                                   #  and every chart is stamped as sample data)

Requirements: pip install pandas matplotlib pymysql
"""

import argparse
import getpass
import os
import sys
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw charts to files; no window is needed
import matplotlib.pyplot as plt
import pandas as pd

# ---------------------------------------------------------------------------
# 1. CONFIGURATION
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
CHART_DIR_NAME = "visualizations"
DATA_DIR_NAME = "output"

# One query joins the three tables. LEFT JOIN keeps readings that have no bill.
# Table and column names are exactly those of src/main/resources/schema.sql.
SQL_QUERY = """
SELECT  r.id               AS reading_id,
        c.id               AS consumer_id,
        c.consumer_number  AS consumer_number,
        c.full_name        AS full_name,
        c.connection_type  AS connection_type,
        r.reading_date     AS reading_date,
        r.previous_reading AS previous_reading,
        r.current_reading  AS current_reading,
        r.units            AS units,
        b.id               AS bill_id,
        b.bill_month       AS bill_month,
        b.amount           AS amount,
        b.payment_status   AS payment_status
FROM readings r
JOIN consumers c ON r.consumer_id = c.id
LEFT JOIN bills b ON b.reading_id = r.id
ORDER BY r.reading_date, r.id
"""

COLUMNS = ["reading_id", "consumer_id", "consumer_number", "full_name", "connection_type",
           "reading_date", "previous_reading", "current_reading", "units",
           "bill_id", "bill_month", "amount", "payment_status"]


# ---------------------------------------------------------------------------
# 2. DATA RETRIEVAL
# ---------------------------------------------------------------------------
def load_from_mysql() -> pd.DataFrame:
    """Connect to MySQL and return the joined data as a DataFrame."""
    try:
        import pymysql  # imported here so that --demo works without the package
    except ImportError:
        sys.exit("PyMySQL is not installed. Run:  pip install pymysql")

    password = os.environ.get("DB_PASSWORD")
    if password is None:
        password = getpass.getpass("MySQL password (input hidden): ")

    settings = {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ.get("DB_USER", "root"),
        "password": password,
        "database": os.environ.get("DB_NAME", "electricity_db"),
    }
    try:
        connection = pymysql.connect(cursorclass=pymysql.cursors.DictCursor, **settings)
    except Exception as error:  # wrong password, server stopped, unknown database ...
        sys.exit(f"Could not connect to MySQL ({settings['host']}:{settings['port']}, "
                 f"database '{settings['database']}'): {error}")

    try:
        with connection.cursor() as cursor:
            cursor.execute(SQL_QUERY)
            rows = cursor.fetchall()
    finally:
        connection.close()

    return pd.DataFrame(rows, columns=COLUMNS)


def make_demo_data() -> pd.DataFrame:
    """ILLUSTRATIVE SAMPLE DATA ONLY - used by --demo to test the script without a database.
    It is NOT output of the real project database."""
    consumers = [(1, "CN-1001", "Sample Consumer 1", "Domestic"),
                 (2, "CN-1002", "Sample Consumer 2", "Domestic"),
                 (3, "CN-1003", "Sample Consumer 3", "Domestic"),
                 (4, "CN-1004", "Sample Consumer 4", "Commercial"),
                 (5, "CN-1005", "Sample Consumer 5", "Commercial"),
                 (6, "CN-1006", "Sample Consumer 6", "Industrial")]
    usage = {1: [142, 158, 171], 2: [96, 110, 104], 3: [230, 262, 248],
             4: [455, 512, 498], 5: [610, 585, 640], 6: [1850, 2100, 1975]}
    start = {1: 1200, 2: 800, 3: 2500, 4: 9000, 5: 12000, 6: 40000}
    dates = ["2026-08-05", "2026-09-05", "2026-10-05"]
    paid = {(1, 0), (1, 1), (2, 0), (3, 0), (3, 1), (3, 2), (4, 0), (4, 1), (5, 0), (6, 0), (6, 1)}
    rows, reading_id = [], 0
    for cid, number, name, kind in consumers:
        reading = start[cid]
        for m, date in enumerate(dates):
            reading_id += 1
            previous, reading = reading, reading + usage[cid][m]
            units = usage[cid][m]
            rows.append([reading_id, cid, number, name, kind, date, previous, reading, units,
                         reading_id, date[:7], 5.00 * units + 30.00,
                         "Paid" if (cid, m) in paid else "Pending"])
    return pd.DataFrame(rows, columns=COLUMNS)


# ---------------------------------------------------------------------------
# 3. PREPROCESSING
# ---------------------------------------------------------------------------
def preprocess(raw: pd.DataFrame):
    """Clean the data. Returns (clean DataFrame, list of log messages)."""
    log = [f"Rows retrieved: {len(raw)}"]
    df = raw.copy()

    # 3.1 Remove spaces and treat empty text as missing
    for column in ["consumer_number", "full_name", "connection_type", "bill_month", "payment_status"]:
        df[column] = df[column].astype("string").str.strip().replace("", pd.NA)

    # 3.2 Convert data types (bad values become NaN / NaT instead of crashing)
    for column in ["previous_reading", "current_reading", "units", "amount"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["reading_date"] = pd.to_datetime(df["reading_date"], errors="coerce")

    # 3.3 Missing values: rows without consumer or date cannot be analysed
    before = len(df)
    df = df.dropna(subset=["consumer_number", "reading_date"])
    log.append(f"Dropped rows with missing consumer number or reading date: {before - len(df)}")

    # 3.4 Units: recompute as current - previous and compare with the stored value
    calculated = df["current_reading"] - df["previous_reading"]
    missing_units = df["units"].isna().sum()
    df["units"] = df["units"].fillna(calculated)
    mismatch = ((df["units"] - calculated).abs() > 0.001).sum()
    log.append(f"Missing 'units' filled from current - previous: {missing_units}")
    log.append(f"Rows where stored units differ from current - previous (kept as stored): {mismatch}")

    # 3.5 Invalid values: units must not be negative or missing
    before = len(df)
    df = df[df["units"].notna() & (df["units"] >= 0)]
    log.append(f"Dropped rows with missing or negative units: {before - len(df)}")

    # 3.6 Duplicate readings
    before = len(df)
    df = df.drop_duplicates(subset=["reading_id"])
    log.append(f"Dropped duplicate reading rows: {before - len(df)}")

    # 3.7 Transformation: month column, payment status for readings without a bill
    df["month"] = df["bill_month"].fillna(df["reading_date"].dt.strftime("%Y-%m"))
    no_bill = df["bill_id"].isna()
    df["payment_status"] = df["payment_status"].fillna("Pending")
    df.loc[no_bill, "payment_status"] = "No Bill"
    log.append(f"Readings without a bill (status set to 'No Bill', excluded from amounts): {int(no_bill.sum())}")

    log.append(f"Rows after cleaning: {len(df)}")
    return df.reset_index(drop=True), log


# ---------------------------------------------------------------------------
# 4. ANALYSIS
# ---------------------------------------------------------------------------
def analyse(df: pd.DataFrame) -> dict:
    """Calculate all summary tables used by the charts and the report."""
    result = {}
    result["total_units"] = float(df["units"].sum())
    result["total_amount"] = float(df["amount"].sum())

    result["by_type"] = df.groupby("connection_type", dropna=False)["units"].sum().reset_index()

    monthly = df.groupby("month").agg(total_units=("units", "sum"), total_amount=("amount", "sum")).reset_index()
    result["monthly"] = monthly.sort_values("month")

    status_month = (df[df["payment_status"].isin(["Paid", "Pending"])]
                    .pivot_table(index="month", columns="payment_status", values="amount",
                                 aggfunc="sum", fill_value=0)
                    .reindex(columns=["Paid", "Pending"], fill_value=0).reset_index())
    result["monthly_status"] = status_month.sort_values("month")

    consumers = (df.groupby(["consumer_number", "full_name"], as_index=False)
                   .agg(total_units=("units", "sum"), readings=("reading_id", "count"),
                        total_amount=("amount", "sum")))
    consumers["average_units_per_reading"] = consumers["total_units"] / consumers["readings"]
    average = consumers["total_units"].mean()
    consumers["usage_category"] = consumers["total_units"].apply(
        lambda units: "High Consumption" if units > average else "Normal Consumption")
    result["consumers"] = consumers.sort_values("total_units", ascending=False).reset_index(drop=True)
    result["average_consumer_units"] = float(average)

    result["by_status"] = (df[df["payment_status"].isin(["Paid", "Pending"])]
                           .groupby("payment_status")["amount"].sum().reindex(["Paid", "Pending"], fill_value=0))
    return result


# ---------------------------------------------------------------------------
# 5. VISUALIZATION
# ---------------------------------------------------------------------------
def stamp(figure, demo: bool):
    """Mark every chart clearly when it was drawn from illustrative sample data."""
    if demo:
        figure.text(0.5, 0.5, "ILLUSTRATIVE SAMPLE DATA\n(not project output)", fontsize=24, color="gray",
                    alpha=0.25, ha="center", va="center", rotation=25)


def save(figure, path: Path, demo: bool):
    stamp(figure, demo)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def draw_charts(r: dict, chart_dir: Path, top_n: int, demo: bool) -> list:
    chart_dir.mkdir(parents=True, exist_ok=True)
    files = []

    # Chart 1 - Total electricity consumption (by connection type)
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(r["by_type"]["connection_type"].astype(str), r["by_type"]["units"])
    ax.set_title(f"Total Electricity Consumption: {r['total_units']:,.0f} units")
    ax.set_xlabel("Connection type"); ax.set_ylabel("Units consumed")
    files.append("1_total_consumption.png"); save(fig, chart_dir / files[-1], demo)

    # Chart 2 - Monthly electricity consumption
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(r["monthly"]["month"], r["monthly"]["total_units"], marker="o")
    ax.set_title("Monthly Electricity Consumption")
    ax.set_xlabel("Month"); ax.set_ylabel("Units consumed"); ax.grid(alpha=0.3)
    files.append("2_monthly_consumption.png"); save(fig, chart_dir / files[-1], demo)

    # Chart 3 - Consumer-wise electricity consumption (with the average line)
    c = r["consumers"]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(c["consumer_number"].astype(str), c["total_units"])
    ax.axhline(r["average_consumer_units"], color="red", linestyle="--",
               label=f"Average = {r['average_consumer_units']:,.0f} units")
    ax.set_title("Consumer-wise Electricity Consumption")
    ax.set_xlabel("Consumer number"); ax.set_ylabel("Total units"); ax.legend()
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    files.append("3_consumerwise_consumption.png"); save(fig, chart_dir / files[-1], demo)

    # Chart 4 - Top high-consumption consumers
    top = c.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(top["consumer_number"].astype(str), top["total_units"])
    ax.set_title(f"Top {min(top_n, len(c))} High-Consumption Consumers")
    ax.set_xlabel("Total units"); ax.set_ylabel("Consumer number")
    files.append("4_top_high_consumption_consumers.png"); save(fig, chart_dir / files[-1], demo)

    # Chart 5 - Monthly bill amount comparison (Paid vs Pending, stacked)
    ms = r["monthly_status"]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(ms["month"], ms["Paid"], label="Paid")
    ax.bar(ms["month"], ms["Pending"], bottom=ms["Paid"], label="Pending")
    ax.set_title("Monthly Bill Amount Comparison")
    ax.set_xlabel("Bill month"); ax.set_ylabel("Amount (Rs.)"); ax.legend()
    files.append("5_monthly_bill_amount.png"); save(fig, chart_dir / files[-1], demo)

    # Chart 6 - Total bill amount (paid vs pending)
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar(r["by_status"].index, r["by_status"].values, color=["tab:green", "tab:orange"])
    ax.set_title(f"Total Bill Amount: Rs. {r['total_amount']:,.2f}")
    ax.set_xlabel("Payment status"); ax.set_ylabel("Amount (Rs.)")
    files.append("6_total_bill_amount.png"); save(fig, chart_dir / files[-1], demo)

    return files


# ---------------------------------------------------------------------------
# 6. SAVE PROCESSED DATA AND REPORT
# ---------------------------------------------------------------------------
def save_outputs(df, r, log, data_dir: Path, charts: list, demo: bool):
    data_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(data_dir / "processed_data.csv", index=False)
    r["consumers"].to_csv(data_dir / "consumer_summary.csv", index=False)
    r["monthly"].to_csv(data_dir / "monthly_summary.csv", index=False)

    high = r["consumers"][r["consumers"]["usage_category"] == "High Consumption"]
    lines = ["ELECTRICITY CONSUMPTION ANALYSIS REPORT",
             f"Generated on : {datetime.now():%Y-%m-%d %H:%M}",
             "Data source  : " + ("ILLUSTRATIVE SAMPLE DATA (--demo), not the project database" if demo
                                  else "MySQL database electricity_db"),
             "", "DATA CLEANING LOG"] + [f"  - {m}" for m in log] + [
             "", "KEY FIGURES",
             f"  Total consumption       : {r['total_units']:,.2f} units",
             f"  Total bill amount       : Rs. {r['total_amount']:,.2f}",
             f"  Paid amount             : Rs. {r['by_status'].get('Paid', 0):,.2f}",
             f"  Pending amount          : Rs. {r['by_status'].get('Pending', 0):,.2f}",
             f"  Consumers analysed      : {len(r['consumers'])}",
             f"  Average per consumer    : {r['average_consumer_units']:,.2f} units",
             "", "MONTHLY CONSUMPTION", r["monthly"].to_string(index=False),
             "", "HIGH-CONSUMPTION CONSUMERS (total units above the consumer average)"]
    lines.append(high.to_string(index=False) if not high.empty else "  None")
    lines += ["", "CHART FILES"] + [f"  - {name}" for name in charts]
    (data_dir / "summary_report.txt").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# 7. MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Electricity consumption analysis")
    parser.add_argument("--demo", action="store_true", help="use illustrative sample data instead of MySQL")
    parser.add_argument("--top-n", type=int, default=5, help="number of consumers in the top-consumers chart")
    args = parser.parse_args()

    sub = "sample_illustrative" if args.demo else ""
    chart_dir = BASE_DIR / CHART_DIR_NAME / sub
    data_dir = BASE_DIR / DATA_DIR_NAME / sub

    raw = make_demo_data() if args.demo else load_from_mysql()
    if raw.empty:
        sys.exit("No meter readings found in the database. Add readings in the web application first.")

    clean, log = preprocess(raw)
    if clean.empty:
        sys.exit("No valid rows left after cleaning. Check the data cleaning rules.")

    results = analyse(clean)
    charts = draw_charts(results, chart_dir, args.top_n, args.demo)
    save_outputs(clean, results, log, data_dir, charts, args.demo)

    print("Analysis completed.")
    print(f"  Charts : {chart_dir}")
    print(f"  Data   : {data_dir}")


if __name__ == "__main__":
    main()
