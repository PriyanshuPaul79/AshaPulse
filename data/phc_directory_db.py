# phc_directory_db.py
# Run this ONCE to convert all JSONs → SQLite database
# Place this file at: Langchain_ASHA/data/phc_directory_db.py
#
# Usage:
#   cd Langchain_ASHA
#   python data/phc_directory_db.py

import sqlite3
import json
import glob
import os
import sys

# ── Paths ────────────────────────────────────────────────────────────────────

# This script lives inside /data/ so we resolve relative to its location
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PHC_JSON_DIR = os.path.join(SCRIPT_DIR, "phc_directory")
DB_PATH      = os.path.join(SCRIPT_DIR, "phc_directory.db")

# ── Valid services master list ────────────────────────────────────────────────
# Only these values are allowed in the services array
# Anything outside this list is flagged during validation

VALID_SERVICES = {
    "OPD",
    "Maternal & Child Health",
    "Immunization",
    "Family Planning",
    "TB DOTS",
    "Malaria Testing",
    "HIV Testing",
    "Nutrition Services",
    "Delivery Services",
    "Minor Surgery",
    "Basic Lab",
    "X-Ray",
    "NCD Screening",
    "Snake Bite Treatment",
    "Dental OPD",
    "Eye OPD",
    "Mental Health",
    "Physiotherapy",
    "Emergency Care",
    "Inpatient Care",
    "Major Surgery",
    "ICU",
    "Blood Bank",
    "CT Scan",
}

# ── Database setup ────────────────────────────────────────────────────────────

def create_tables(cursor: sqlite3.Cursor) -> None:
    """Create all tables and indexes. Safe to run multiple times."""

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS phcs (
            id              TEXT PRIMARY KEY,
            name            TEXT NOT NULL,
            block           TEXT,
            district        TEXT NOT NULL,
            state           TEXT NOT NULL,
            address         TEXT,
            pin_code        TEXT,
            contact         TEXT,
            open_24hr       INTEGER DEFAULT 0,
            doctor_timing   TEXT,
            ambulance       INTEGER DEFAULT 0,
            latitude        REAL,
            longitude       REAL,
            confidence      TEXT,
            emergency_capable  INTEGER DEFAULT 0,
            facility_level     INTEGER DEFAULT 1,
            facility_type      TEXT
        );

        CREATE TABLE IF NOT EXISTS phc_services (
            phc_id      TEXT NOT NULL,
            service     TEXT NOT NULL,
            FOREIGN KEY (phc_id) REFERENCES phcs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_district
            ON phcs(district);

        CREATE INDEX IF NOT EXISTS idx_state
            ON phcs(state);

        CREATE INDEX IF NOT EXISTS idx_service
            ON phc_services(service);

        CREATE INDEX IF NOT EXISTS idx_phc_service_pair
            ON phc_services(phc_id, service);
    """)


# ── JSON loading ──────────────────────────────────────────────────────────────

def load_json_file(filepath: str) -> dict | None:
    """Load and parse a single JSON file. Returns None on error."""
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON parse error in {filepath}: {e}")
        return None
    except Exception as e:
        print(f"  ❌ Could not read {filepath}: {e}")
        return None


# ── Validation ────────────────────────────────────────────────────────────────

def validate_phc(phc: dict, district: str) -> list[str]:
    """
    Validate a single PHC entry.
    Returns a list of warning strings (empty = all good).
    """
    warnings = []

    if not phc.get("id"):
        warnings.append("Missing 'id' field")
    if not phc.get("name"):
        warnings.append("Missing 'name' field")

    # Coordinate sanity check for West Bengal
    # WB bounding box: lat 21.5–27.2, lon 85.8–89.9
    lat = phc.get("latitude")
    lon = phc.get("longitude")
    if lat is not None and lon is not None:
        if not (21.5 <= lat <= 27.2):
            warnings.append(f"Latitude {lat} outside West Bengal range")
        if not (85.8 <= lon <= 89.9):
            warnings.append(f"Longitude {lon} outside West Bengal range")

    # Service validation
    invalid_services = [
        s for s in phc.get("services", [])
        if s not in VALID_SERVICES
    ]
    if invalid_services:
        warnings.append(f"Unknown services: {invalid_services}")

    # Confidence check
    confidence = phc.get("confidence", "")
    if confidence not in ("high", "medium", "low", ""):
        warnings.append(f"Unexpected confidence value: '{confidence}'")

    return warnings


# ── Insertion ─────────────────────────────────────────────────────────────────

def insert_phc(cursor: sqlite3.Cursor, phc: dict,
               district: str, state: str) -> None:
    """Insert one PHC + its services into the database."""

    cursor.execute("""
        INSERT OR REPLACE INTO phcs (
            id, name, block, district, state,
            address, pin_code, contact,
            open_24hr, doctor_timing, ambulance,
            latitude, longitude, confidence,emergency_capable, facility_level, facility_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
    """, (
        phc.get("id"),
        phc.get("name"),
        phc.get("block"),
        district,
        state,
        phc.get("address"),
        phc.get("pin_code"),
        phc.get("contact"),
        1 if phc.get("open_24hr") else 0,
        phc.get("doctor_timing"),
        1 if phc.get("ambulance") else 0,
        phc.get("latitude"),
        phc.get("longitude"),
        phc.get("confidence"),
        1 if phc.get("emergency_capable") else 0,
        phc.get("facility_level", 1),
        phc.get("facility_type"),
    ))

    # Delete old services for this PHC before re-inserting
    # (handles re-runs cleanly)
    cursor.execute(
        "DELETE FROM phc_services WHERE phc_id = ?",
        (phc["id"],)
    )

    for service in phc.get("services", []):
        if service in VALID_SERVICES:   # only insert valid services
            cursor.execute(
                "INSERT INTO phc_services (phc_id, service) VALUES (?, ?)",
                (phc["id"], service)
            )


# ── Main build function ───────────────────────────────────────────────────────

def build_database() -> None:
    print("\n" + "═" * 55)
    print("  ASHA PHC Directory — Database Builder")
    print("═" * 55)
    print(f"  JSON source : {PHC_JSON_DIR}")
    print(f"  Database    : {DB_PATH}")
    print("═" * 55 + "\n")

    # Find all JSON files recursively inside phc_directory/
    json_files = sorted(
        glob.glob(os.path.join(PHC_JSON_DIR, "**", "*.json"),
                  recursive=True)
    )

    if not json_files:
        print("❌ No JSON files found.")
        print(f"   Expected location: {PHC_JSON_DIR}/west_bengal/*.json")
        sys.exit(1)

    print(f"Found {len(json_files)} JSON file(s):\n")
    for f in json_files:
        print(f"  → {os.path.relpath(f, SCRIPT_DIR)}")
    print()

    # Connect and set up database
    conn   = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    create_tables(cursor)

    # Counters for summary
    total_inserted  = 0
    total_warnings  = 0
    total_skipped   = 0
    district_counts = {}

    # Process each JSON file
    for filepath in json_files:
        filename = os.path.basename(filepath)
        print(f"Processing: {filename}")

        data = load_json_file(filepath)
        if data is None:
            total_skipped += 1
            continue

        state    = data.get("state", "Unknown")
        district = data.get("district", "Unknown")
        phcs     = data.get("phcs", [])

        if not phcs:
            print(f"  ⚠️  No PHCs found in {filename}")
            continue

        inserted_this_file = 0
        for phc in phcs:
            # Validate
            warnings = validate_phc(phc, district)
            if warnings:
                print(f"  ⚠️  {phc.get('id', '???')} — {'; '.join(warnings)}")
                total_warnings += len(warnings)

            # Insert regardless of warnings
            # (warnings are informational, not blockers)
            try:
                insert_phc(cursor, phc, district, state)
                inserted_this_file += 1
            except Exception as e:
                print(f"  ❌ Failed to insert {phc.get('id')}: {e}")
                total_skipped += 1

        total_inserted += inserted_this_file
        district_counts[district] = inserted_this_file
        print(f"  ✅ {inserted_this_file} PHCs inserted — {district}, {state}\n")

    conn.commit()

    # ── Summary ───────────────────────────────────────────────────────────────
    print("═" * 55)
    print("  BUILD COMPLETE")
    print("═" * 55)
    print(f"  Total PHCs inserted : {total_inserted}")
    print(f"  Validation warnings : {total_warnings}")
    print(f"  Files skipped       : {total_skipped}")
    print()
    print("  District breakdown:")
    for district, count in district_counts.items():
        print(f"    {district:<30} {count} PHCs")
    print()

    # ── Quick DB verification ─────────────────────────────────────────────────
    print("  Database verification:")

    cursor.execute("SELECT COUNT(*) FROM phcs")
    phc_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM phc_services")
    service_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM phcs WHERE latitude IS NOT NULL")
    geo_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM phcs WHERE contact IS NOT NULL")
    contact_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM phcs WHERE open_24hr = 1")
    open_24hr_count = cursor.fetchone()[0]

    print(f"    Total PHC records      : {phc_count}")
    print(f"    Total service entries  : {service_count}")
    print(f"    PHCs with coordinates  : {geo_count}/{phc_count}")
    print(f"    PHCs with contact no.  : {contact_count}/{phc_count}")
    print(f"    24hr PHCs              : {open_24hr_count}/{phc_count}")

    # Top services
    cursor.execute("""
        SELECT service, COUNT(*) as cnt
        FROM phc_services
        GROUP BY service
        ORDER BY cnt DESC
        LIMIT 5
    """)
    top_services = cursor.fetchall()
    if top_services:
        print("\n  Top 5 services across all PHCs:")
        for service, count in top_services:
            print(f"    {service:<30} {count} PHCs")

    print("\n" + "═" * 55)
    print(f"  ✅ Database ready at: {DB_PATH}")
    print("═" * 55 + "\n")

    conn.close()


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    build_database()
