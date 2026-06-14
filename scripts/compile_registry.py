import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

def get_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def compile_registry(
    input_path: str = "registry/government_directory.json",
    output_dir: str = "registry/domains",
    db_path: str = "registry/government_directory.db"
):
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Input file {input_path} not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Output domain-specific JSON files
    domains = {}
    for item in data:
        domain = get_domain(item["official_website"])
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(item)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Clean up old domain files
    for f in output_path.glob("*.json"):
        f.unlink()

    for domain, items in domains.items():
        with open(output_path / f"{domain}.json", "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False)
    
    print(f"Compiled {len(data)} agencies into {len(domains)} domain files.")

    # 2. Export to SQLite (Phase 1 Task 4)
    export_to_sqlite(data, db_path)

def export_to_sqlite(data: list, db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop tables if they exist
    cursor.execute("DROP TABLE IF EXISTS social_profiles")
    cursor.execute("DROP TABLE IF EXISTS agencies")

    # Create tables
    cursor.execute("""
        CREATE TABLE agencies (
            agency_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT,
            portfolio TEXT,
            official_website TEXT,
            status TEXT,
            parent_agency_id TEXT,
            domain TEXT,
            FOREIGN KEY (parent_agency_id) REFERENCES agencies (agency_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE social_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agency_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            deactivated_at TEXT,
            reason TEXT,
            alternative_url TEXT,
            FOREIGN KEY (agency_id) REFERENCES agencies (agency_id)
        )
    """)

    for item in data:
        domain = get_domain(item["official_website"])
        cursor.execute("""
            INSERT INTO agencies (agency_id, name, type, portfolio, official_website, status, parent_agency_id, domain)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item["agency_id"],
            item["name"],
            item.get("type"),
            item.get("portfolio"),
            item["official_website"],
            item["status"],
            item.get("parent_agency_id"),
            domain
        ))

        for platform, profile in item.get("social_profiles", {}).items():
            cursor.execute("""
                INSERT INTO social_profiles (agency_id, platform, handle, url, status, deactivated_at, reason, alternative_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item["agency_id"],
                platform,
                profile["handle"],
                profile["url"],
                profile["status"],
                profile.get("deactivated_at"),
                profile.get("reason"),
                profile.get("alternative_url")
            ))

    conn.commit()
    conn.close()
    print(f"Exported registry to SQLite: {db_path}")

if __name__ == "__main__":
    compile_registry()
