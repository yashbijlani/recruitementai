import argparse

from app.core.config import resolve_path, settings
from app.db import SessionLocal
from app.ingestion.excel import import_workbook


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import the candidate master workbook idempotently.")
    parser.add_argument("--file", default=settings.seed_file)
    parser.add_argument("--organization", default="Demo Recruitment")
    args = parser.parse_args()
    with SessionLocal() as session:
        stats = import_workbook(session, resolve_path(args.file), args.organization)
    print("Reading candidate database...")
    print(f"Rows found: {stats['rows_read']}")
    print(f"Valid rows: {stats['valid_rows']}")
    print(f"Inserted: {stats['inserted']}")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {stats['errors']}")
    print("\nImport complete.")
