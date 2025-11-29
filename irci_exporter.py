#!/usr/bin/env python3
"""
irci_exporter.py — Bridge your existing outputs to Excel/Google Sheets
"""
import argparse, json, os, sys, datetime as dt
import pandas as pd

CANONICAL_SHEETS = ["FILINGS","PRICES","FACTORS","EVENTS","NEWS","DIALS","COMPOSITE"]

def load_csvs_from_dir(d):
    frames = {}
    for name in CANONICAL_SHEETS:
        path = os.path.join(d, f"{name}.csv")
        if os.path.exists(path):
            frames[name] = pd.read_csv(path)
        else:
            frames[name] = pd.DataFrame()
    return frames

def write_excel(frames, excel_path):
    # Preserve existing template sheets if present; otherwise create new
    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        for name, df in frames.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return excel_path

def write_google_sheets(frames, sheet_name):
    # Optional: requires gspread + Google service account creds (JSON)
    import gspread
    from gspread_dataframe import set_with_dataframe
    gc = gspread.service_account()
    sh = gc.open(sheet_name)
    for name, df in frames.items():
        try:
            ws = sh.worksheet(name)
            ws.clear()
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title=name, rows=str(max(len(df)+10, 100)), cols="26")
        set_with_dataframe(ws, df, include_index=False, include_column_header=True, resize=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-exports", help="Directory with CSVs named FILINGS/PRICES/FACTORS/EVENTS/NEWS/DIALS/COMPOSITE.csv")
    ap.add_argument("--excel", help="Path to Excel template to overwrite (e.g., IRCI_lowcode_template.xlsx)")
    ap.add_argument("--google-sheet", help="Google Sheet name to write (requires gspread)")
    ap.add_argument("--manifest", default="manifest.json", help="Optional path to write a small manifest")
    args = ap.parse_args()

    if not (args.from_exports and (args.excel or args.google_sheet)):
        ap.error("Provide --from-exports and either --excel or --google-sheet")

    frames = load_csvs_from_dir(args.from_exports)

    # Basic column coercions (optional): ensure Date-like columns parse correctly
    for nm in ["FILINGS","PRICES","FACTORS","EVENTS","NEWS"]:
        if not frames[nm].empty:
            for col in [c for c in frames[nm].columns if "Date" in c or c in ("WindowStart","WindowEnd")]:
                try:
                    frames[nm][col] = pd.to_datetime(frames[nm][col]).dt.date
                except Exception:
                    pass

    if args.excel:
        write_excel(frames, args.excel)
        target = args.excel
    if args.google_sheet:
        write_google_sheets(frames, args.google_sheet)
        target = args.google_sheet

    # Write a tiny manifest for reproducibility
    manifest = {
        "export_time_utc": dt.datetime.utcnow().isoformat() + "Z",
        "source_dir": os.path.abspath(args.from_exports),
        "targets": {"excel": args.excel, "google_sheet": args.google_sheet},
        "tables_written": {k: int(len(v)) for k,v in frames.items()},
    }
    with open(args.manifest, "w") as f:
        json.dump(manifest, f, indent=2)
    print("Wrote:", target)
    print("Manifest:", os.path.abspath(args.manifest))

if __name__ == "__main__":
    main()
