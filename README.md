# Electricity Consumption Management and Energy Usage Analysis System

A web-based college project (Scenario No. 14) that manages electricity consumers, validates meter readings, generates bills with a demonstration tariff, tracks payment status and supports energy usage analysis with Python.

> **Tariff note:** the bill is calculated as `5.00 × units + 30.00`. This is a **demonstration tariff**, not an official electricity tariff.

---

## Problem Statement

Recording consumers, meter readings and bills on paper or in separate spreadsheets is slow and error-prone. This project stores all data in one MySQL database, rejects a current reading lower than the previous reading, calculates units and bills automatically, shows dashboard totals and monthly usage, and lets Python analyse consumption patterns.

## Features

Implemented (verified in the source code):

- Administrator login / logout (fixed demo credentials `admin` / `admin123`)
- Consumer management: add, list, delete (update is available through the REST API only)
- Meter reading entry: current reading lower than the previous reading is rejected; `units = current − previous`
- Automatic bill generation for every reading (status `Pending`), bill listing, **Mark Paid**
- Dashboard: total consumers, total units, billed amount, unpaid bills, month-wise usage table
- CSV consumption report download
- Python analysis: consumer-wise usage, high-consumption consumers (above average), charts

Not implemented (proposed): secure authentication, tariff slabs, payment records, bill PDF, edit form and single-consumer view in the web page, automated unit tests. See *Future Enhancements*.

## Technologies Used

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript (served by Spring Boot from `static/`) |
| Backend | Java 17, Spring Boot 3.4.4, REST API, Maven, `JdbcTemplate` |
| Database | MySQL (`electricity_db`) |
| Analysis | Python, Pandas, Matplotlib, PyMySQL |
| Tools | Visual Studio Code, Windows, Google Chrome |

## Project Folder Structure

```
Electricity proj/                         (the application)
├── pom.xml
├── src/main/java/com/college/electricity/ElectricityApplication.java
├── src/main/resources/
│   ├── application.properties            (contains the DB user/password - do NOT publish)
│   ├── schema.sql
│   └── static/  index.html  style.css  app.js
└── python-analysis/  analyze.py  requirements.txt

Electricity-Consumption-Management-Documentation/   (documentation package)
├── Main_Documentation/Electricity_Consumption_Management_System_Documentation.docx
├── Diagrams/            Use case, Class, Architecture, ER, DFD 0, DFD 1, Relational schema
│                        (.puml / .mmd / .dot sources + PNG previews)
├── Database/            Database_Design.docx, Normalization.docx, SQL_Scripts/
├── Testing/             Electricity_Project_Test_Cases.docx
├── Python_Analysis/     Python_Data_Analysis.docx, electricity_analysis.py, visualizations/
└── README.md
```

## Database Setup

1. Install MySQL Server and start the service.
2. The application creates the database and tables by itself (`createDatabaseIfNotExist=true` and `schema.sql`).
3. Optional manual setup in MySQL Workbench or the `mysql` client:
   ```sql
   SOURCE Database/SQL_Scripts/01_create_schema.sql;
   SOURCE Database/SQL_Scripts/02_sample_data.sql;   -- illustrative sample rows, test database only
   ```

## MySQL Configuration

Edit `src/main/resources/application.properties`:

```properties
spring.datasource.url=jdbc:mysql://localhost:3306/electricity_db?createDatabaseIfNotExist=true&useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Kolkata
spring.datasource.username=root
spring.datasource.password=<your-mysql-password>
```

**Never commit your real password.** Before uploading to GitHub, replace it with a placeholder (or use environment variables) and add `target/` to `.gitignore`.

## Backend Execution

```bash
cd "Electricity proj"
mvn spring-boot:run
# or:  mvn clean package   then   java -jar target/electricity-management-1.0.0.jar
```

The backend runs at **http://localhost:8080** (port 8080).

## Frontend Execution

There is no separate frontend server. Spring Boot serves the pages: open **http://localhost:8080** in Google Chrome and log in with `admin` / `admin123`. Do not open `index.html` directly from disk, because the page calls the relative path `/api`.

## API Endpoint Summary

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/health` | Application status |
| POST | `/api/login` | Admin login |
| GET | `/api/dashboard` | Dashboard totals |
| POST | `/api/consumers` | Add consumer |
| GET | `/api/consumers` | List consumers |
| PUT | `/api/consumers/{id}` | Update consumer |
| DELETE | `/api/consumers/{id}` | Delete consumer (and its readings and bills) |
| POST | `/api/readings` | Save reading and generate bill |
| GET | `/api/readings` | List readings |
| GET | `/api/bills` | List bills |
| PUT | `/api/bills/{id}/pay` | Mark bill as Paid |
| GET | `/api/analysis/monthly` | Monthly units and amount |
| GET | `/api/reports/consumption.csv` | Download CSV report |

## Python Installation

```bash
cd Python_Analysis
pip install pandas matplotlib pymysql
```

(The existing `python-analysis/analyze.py` needs `pip install -r requirements.txt`, i.e. pandas, matplotlib and requests.)

## Python Execution

```powershell
$env:DB_HOST="localhost"; $env:DB_PORT="3306"; $env:DB_USER="root"
$env:DB_PASSWORD="<your-mysql-password>"; $env:DB_NAME="electricity_db"
python electricity_analysis.py             # real data from MySQL
python electricity_analysis.py --demo      # illustrative sample data (no database needed)
```

If `DB_PASSWORD` is not set the script asks for it. Results are written to `visualizations/` (charts) and `output/` (processed data and `summary_report.txt`).

> `python-analysis/analyze.py` in the project reads the CSV endpoint and uses the column names `Consumer Name` / `Units Consumed`, while the CSV header is `Name` / `Units`; correct this before using it.

## Visualization Outputs

`electricity_analysis.py` creates six charts: total consumption, monthly consumption, consumer-wise consumption, top high-consumption consumers, monthly bill amount comparison (Paid vs Pending) and total bill amount.

The files in `Python_Analysis/visualizations/sample_illustrative/` are drawn from **illustrative sample data** and are watermarked. Replace them with charts from your own database before submission.

## Screenshots

Add your screenshots to a `screenshots/` folder and link them here:

| Page | Screenshot |
|---|---|
| Login | `screenshots/login.png` *(to be added)* |
| Dashboard | `screenshots/dashboard.png` *(to be added)* |
| Consumer Management | `screenshots/consumers.png` *(to be added)* |
| Meter Reading | `screenshots/readings.png` *(to be added)* |
| Bill Management | `screenshots/bills.png` *(to be added)* |
| Energy Analysis | `screenshots/analysis.png` *(to be added)* |

## Testing

Test cases for every module (positive and negative) are in `Testing/Electricity_Project_Test_Cases.docx`. The project has no automated JUnit tests. Test cases are **Not Executed** until you run them and fill in the *Actual Result* and *Status* columns.

## Known Limitations

Demo login only, limited server-side validation, phone number not stored, dashboard card "Paid Revenue" sums all bills, all backend code in one class. The full list (KI-1 to KI-12) is in the main documentation, Chapter 4.

## Future Enhancements (not implemented)

Spring Security login, server-side validation, controller/service/repository/entity layers, slab-based tariff table, edit form and consumer detail page, payment records, charts in the web dashboard, PDF bills, JUnit tests.

## License / Author

Student: `[STUDENT NAME]` · College: `[COLLEGE NAME]` · Guide: `[GUIDE NAME]`
