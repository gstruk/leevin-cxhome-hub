# Collection Risk — Data Update Workflow

Run this workflow **Monday / Wednesday / Friday** (or after any significant payment activity).

---

## Step 1 — Export from BeeMyRoom

1. Log in to BeeMyRoom → **Finance → Bills**
2. Set date range: **01 Jan [current year]** to **today**
3. Click **Export → CSV (Financial Report — Bills)**
4. Save the file somewhere convenient, e.g. `Downloads/`

---

## Step 2 — Prepare the CSV

Open the file in a text editor or Excel and confirm:

- **Delete** any columns that are NOT in the list below before saving
- **Never add** name, email, phone, or any nominal/PII columns
- Save as **CSV UTF-8** (Excel: *Save As → CSV UTF-8 (Comma delimited)*)

### Required column order (exactly 17 columns)

| # | Column name | Notes |
|---|------------|-------|
| 1 | `booking_number` | Booking reference |
| 2 | `bill_number` | Unique bill ID |
| 3 | `customer_id` | Anonymised customer identifier — **the only customer identifier allowed** |
| 4 | `property` | Property name |
| 5 | `brand` | Brand / portfolio |
| 6 | `city` | City |
| 7 | `room` | Room code |
| 8 | `bed` | Bed code |
| 9 | `last_paid_date` | ISO date YYYY-MM-DD or DD/MM/YYYY |
| 10 | `last_payment_method` | e.g. Bank transfer, Cash |
| 11 | `due_date` | ISO date YYYY-MM-DD or DD/MM/YYYY |
| 12 | `item_types` | e.g. Room fee, Deposit, Fee - Late payment |
| 13 | `item_descriptions` | Free text description |
| 14 | `status` | e.g. Pending, Partially paid, Fully paid |
| 15 | `remaining_amount` | Numeric, e.g. 125.00 |
| 16 | `paid_amount` | Numeric |
| 17 | `total_amount` | Numeric |

PII rule: The file must never contain tenant names, email addresses, phone numbers, or passport/ID numbers. customer_id is the only customer identifier and must be an opaque code from BeeMyRoom, not a real name.

---

## Step 3 — Push the update

### Option A — Python script (recommended)

Run from your Claude .claude directory:

    python update_collection_risk.py "C:\path\to\your-export.csv"

The script will:
- Parse and validate the CSV
- Classify overdue bills by risk tier (C / B / A)
- Push the updated data/collection-data.csv to GitHub
- Confirm the live URL

### Option B — Manual GitHub upload

1. Go to https://github.com/gstruk/leevin-cxhome-hub/tree/main/data
2. Click Add file → Upload files
3. Drop your prepared CSV and name it exactly collection-data.csv
4. Commit directly to main

---

## Step 4 — Verify

Open https://gstruk.github.io/leevin-cxhome-hub/collection-risk.html and confirm:

- Last updated badge shows today's date/time
- Total Outstanding and Overdue Amount KPIs match expectations
- No amber "Data may be outdated" warning bar is visible
- Charts show data up to the current month

---

## Freshness reminder

The dashboard automatically shows an amber warning if the newest last_paid_date in the data is more than 7 days old. If you see this, run the update workflow.

---

## Column validation

The Python update script validates that all 17 required columns are present and exits with a clear error if any are missing. Compare your CSV header row to the table in Step 2 if you see a validation error.