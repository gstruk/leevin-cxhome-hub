"""
CX Team Dashboard Updater
--------------------------
1. Export the Google Sheet as CSV:
   File > Download > Comma-separated values (.csv)
   Save to your Downloads folder.

2. Run this script:
   python update_cx_dashboard.py

It will:
  - Find the latest tickets_management_overview*.csv in Downloads
  - Parse all monthly tables
  - Update the JS data block in cx-team-dashboard.html
  - Push cx-team.html to GitHub Pages (leevin-cxhome-hub repo)
"""

import csv, re, os, glob, json, base64, urllib.request, urllib.error, sys, calendar
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE  = os.path.join(SCRIPT_DIR, "cx-team-dashboard.html")
CFG_FILE   = os.path.join(SCRIPT_DIR, "..", "github_config.json")

MONTH_ORDER = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]

SHORT_LABELS = {
    "January":"Jan","February":"Feb","March":"Mar","April":"Apr",
    "May":"May","June":"Jun","July":"Jul","August":"Aug",
    "September":"Sep","October":"Oct","November":"Nov","December":"Dec"
}

LOC_MAP = {
    "CX Home Brazil":   "Brazil",
    "CX Home Cork":     "Cork",
    "CX Home Dublin":   "Dublin",
    "CX Home Limerick": "Limerick",
}


def find_csv():
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    files = glob.glob(os.path.join(downloads, "tickets_management_overview*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No CSV found in Downloads matching: tickets_management_overview*.csv\n"
            "Export the sheet: File > Download > Comma-separated values (.csv)"
        )
    latest = max(files, key=os.path.getmtime)
    print(f"  Using: {os.path.basename(latest)}")
    return latest


def parse_csv(path):
    months = []
    current_key    = None
    current_agents = []
    in_data        = False

    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.reader(f):
            if not any(c.strip() for c in row):
                continue
            first = row[0].strip()

            # Month header row e.g. "May/2026"
            if re.match(r'^[A-Za-z]+/\d{4}$', first):
                if current_key and current_agents:
                    months.append(_make_month(current_key, current_agents))
                current_key    = first
                current_agents = []
                in_data        = False
                continue

            # Column header row
            if first.lower() == "agent name":
                in_data = True
                continue

            if not in_data or not current_key:
                continue

            # Totals row (first cell is a plain integer)
            if re.match(r'^\d+$', first):
                continue

            # Agent row
            if len(row) >= 7:
                try:
                    current_agents.append({
                        "name":       row[0].strip(),
                        "loc":        LOC_MAP.get(row[1].strip(), row[1].strip()),
                        "unresolved": int(row[2]),
                        "created":    int(row[3]),
                        "resolved":   int(row[4]),
                        "reopened":   int(row[5]),
                        "pct":        float(row[6]),
                    })
                except (ValueError, IndexError):
                    pass

    if current_key and current_agents:
        months.append(_make_month(current_key, current_agents))

    # Sort newest first
    def sort_key(m):
        name, year = m["key"].split("/")
        idx = MONTH_ORDER.index(name) if name in MONTH_ORDER else 0
        return (int(year), idx)

    months.sort(key=sort_key, reverse=True)
    return months


def working_days_in_month(key):
    name, yr = key.split("/")
    mi = MONTH_ORDER.index(name) + 1 if name in MONTH_ORDER else 1
    y = int(yr)
    _, last = calendar.monthrange(y, mi)
    return sum(1 for d in range(1, last + 1) if date(y, mi, d).weekday() < 5)


def _make_month(key, agents):
    name, year = key.split("/")
    wdays = working_days_in_month(key)
    for a in agents:
        a["resolvedPerDay"] = round(a["resolved"] / wdays, 2) if wdays > 0 else 0
    return {"label": f"{SHORT_LABELS.get(name, name)} {year}", "key": key, "agents": agents}


def months_to_js(months):
    def fmt_agents(agents):
        lines = []
        for a in agents:
            lines.append(
                f'      {{ name: {json.dumps(a["name"])}, loc: {json.dumps(a["loc"])}, '
                f'unresolved: {a["unresolved"]}, created: {a["created"]}, '
                f'resolved: {a["resolved"]}, reopened: {a["reopened"]}, pct: {a["pct"]}, '
                f'resolvedPerDay: {a["resolvedPerDay"]} }}'
            )
        return ",\n".join(lines)

    blocks = []
    for m in months:
        blocks.append(
            f'  {{\n'
            f'    label: {json.dumps(m["label"])}, key: {json.dumps(m["key"])},\n'
            f'    agents: [\n{fmt_agents(m["agents"])}\n    ]\n'
            f'  }}'
        )
    return "[\n" + ",\n".join(blocks) + "\n]"


def update_html(months):
    today = date.today().isoformat()

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        html = f.read()

    replacement = (
        f"/* DATA_START */\n"
        f"const MONTHS_DATA = {months_to_js(months)};\n"
        f"const DATA_UPDATED = \"{today}\";\n"
        f"/* DATA_END */"
    )

    html_new, n = re.subn(
        r'/\* DATA_START \*/.*?/\* DATA_END \*/',
        replacement, html, count=1, flags=re.DOTALL
    )

    if n != 1:
        raise RuntimeError("DATA_START/DATA_END markers not found in cx-team-dashboard.html.")

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(html_new)

    total_agents = sum(len(m["agents"]) for m in months)
    print(f"  Updated HTML: {len(months)} months, {total_agents} agent records, date={today}")


def push_to_github():
    with open(CFG_FILE) as f:
        cfg = json.load(f)

    token = cfg["token"]
    owner = cfg["owner"]
    repo  = "leevin-cxhome-hub"
    hdrs  = {"Authorization": f"token {token}", "Content-Type": "application/json", "User-Agent": "update-cx-dashboard"}
    url   = f"https://api.github.com/repos/{owner}/{repo}/contents/cx-team.html"

    with open(HTML_FILE, "rb") as f:
        content = base64.b64encode(f.read()).decode()

    try:
        res = urllib.request.urlopen(urllib.request.Request(url, headers=hdrs), timeout=30)
        sha = json.loads(res.read()).get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            sha = None
        else:
            raise

    body = {"message": "Update CX team dashboard data", "content": content}
    if sha:
        body["sha"] = sha

    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdrs, method="PUT")
    urllib.request.urlopen(req, timeout=120)
    print(f"  Pushed: https://{owner}.github.io/{repo}/cx-team.html")


if __name__ == "__main__":
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("CX Team Dashboard Updater")
    print("=" * 40)

    csv_path = find_csv()
    months   = parse_csv(csv_path)

    if not months:
        print("ERROR: No monthly data parsed from CSV. Check file format.")
        sys.exit(1)

    print(f"  Months found: {', '.join(m['label'] for m in months)}")
    update_html(months)
    push_to_github()

    print("=" * 40)
    print("Done.")
