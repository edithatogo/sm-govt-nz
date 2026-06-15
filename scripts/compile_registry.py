import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

def get_domain(url: str) -> str:
    if not url:
        return "missing-official-website"
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def compile_registry(
    input_path: str = "registry/government_directory.json",
    output_dir: str = "registry/domains",
    db_path: str = "registry/government_directory.db",
    parties_path: str = "registry/parties.json",
    persons_path: str = "registry/persons.json",
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

    # 2. Load parties and persons data
    parties_data = []
    parties_file = Path(parties_path)
    if parties_file.exists():
        with open(parties_file, "r", encoding="utf-8") as f:
            parties_data = json.load(f)
        print(f"Loaded {len(parties_data)} political parties.")

    persons_data = []
    persons_file = Path(persons_path)
    if persons_file.exists():
        with open(persons_file, "r", encoding="utf-8") as f:
            persons_data = json.load(f)
        print(f"Loaded {len(persons_data)} persons.")

    # 3. Export to SQLite
    export_to_sqlite(data, parties_data, persons_data, db_path)

def export_to_sqlite(data: list, parties_data: list, persons_data: list, db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop tables if they exist
    cursor.execute("DROP TABLE IF EXISTS tenure_linked_profiles")
    cursor.execute("DROP TABLE IF EXISTS person_social_profiles")
    cursor.execute("DROP TABLE IF EXISTS person_roles")
    cursor.execute("DROP TABLE IF EXISTS persons")
    cursor.execute("DROP TABLE IF EXISTS party_social_profiles")
    cursor.execute("DROP TABLE IF EXISTS parties")
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

    cursor.execute("""
        CREATE TABLE parties (
            party_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            name_maori TEXT,
            short_name TEXT,
            founded TEXT,
            registered TEXT,
            deregistered TEXT,
            status TEXT NOT NULL,
            website TEXT,
            logo_url TEXT,
            leader_person_id TEXT,
            president_person_id TEXT,
            seats_in_parliament INTEGER,
            political_position TEXT,
            colour TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE party_social_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (party_id) REFERENCES parties (party_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE persons (
            person_id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            preferred_name TEXT,
            honorific TEXT,
            party_id TEXT,
            electorate TEXT,
            list_rank INTEGER,
            member_type TEXT,
            gender TEXT,
            image_url TEXT,
            biography_url TEXT,
            FOREIGN KEY (party_id) REFERENCES parties (party_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE person_roles (
            role_id TEXT NOT NULL,
            person_id TEXT NOT NULL,
            title TEXT NOT NULL,
            organization TEXT,
            organization_name TEXT,
            category TEXT NOT NULL,
            portfolio TEXT,
            start_date TEXT,
            end_date TEXT,
            is_current INTEGER NOT NULL,
            PRIMARY KEY (role_id, person_id),
            FOREIGN KEY (person_id) REFERENCES persons (person_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE person_social_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            url TEXT NOT NULL,
            status TEXT NOT NULL,
            is_verified INTEGER,
            FOREIGN KEY (person_id) REFERENCES persons (person_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE tenure_linked_profiles (
            profile_id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id TEXT NOT NULL,
            platform TEXT NOT NULL,
            handle TEXT NOT NULL,
            url TEXT NOT NULL,
            role_id TEXT NOT NULL,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY (person_id) REFERENCES persons (person_id)
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

    # Insert parties data
    for party in parties_data:
        cursor.execute("""
            INSERT INTO parties (party_id, name, name_maori, short_name, founded, registered, deregistered, status, website, logo_url, leader_person_id, president_person_id, seats_in_parliament, political_position, colour)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            party["party_id"],
            party["name"],
            party.get("name_maori") or party.get("name_māori"),
            party.get("short_name"),
            party.get("founded"),
            party.get("registered"),
            party.get("deregistered"),
            party["status"],
            party.get("website"),
            party.get("logo_url"),
            party.get("leader_person_id"),
            party.get("president_person_id"),
            party.get("seats_in_parliament"),
            party.get("political_position"),
            party.get("colour")
        ))
        for platform, profile in party.get("social_profiles", {}).items():
            cursor.execute("""
                INSERT INTO party_social_profiles (party_id, platform, handle, url, status)
                VALUES (?, ?, ?, ?, ?)
            """, (party["party_id"], platform, profile["handle"], profile["url"], profile["status"]))

    # Insert persons data
    for person in persons_data:
        cursor.execute("""
            INSERT INTO persons (person_id, full_name, preferred_name, honorific, party_id, electorate, list_rank, member_type, gender, image_url, biography_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            person["person_id"],
            person["full_name"],
            person.get("preferred_name"),
            person.get("honorific"),
            person.get("party_id"),
            person.get("electorate"),
            person.get("list_rank"),
            person.get("member_type"),
            person.get("gender"),
            person.get("image_url"),
            person.get("biography_url")
        ))
        for role in person.get("roles", []):
            cursor.execute("""
                INSERT INTO person_roles (role_id, person_id, title, organization, organization_name, category, portfolio, start_date, end_date, is_current)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                role["role_id"],
                person["person_id"],
                role["title"],
                role.get("organization"),
                role.get("organization_name"),
                role["category"],
                role.get("portfolio"),
                role.get("start_date"),
                role.get("end_date"),
                1 if role.get("is_current") else 0
            ))
        for platform, profile in person.get("social_profiles", {}).items():
            cursor.execute("""
                INSERT INTO person_social_profiles (person_id, platform, handle, url, status, is_verified)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                person["person_id"],
                platform,
                profile["handle"],
                profile["url"],
                profile["status"],
                1 if profile.get("is_verified") else 0 if "is_verified" in profile else None
            ))
        for tlp in person.get("tenure_linked_profiles", []):
            cursor.execute("""
                INSERT INTO tenure_linked_profiles (person_id, platform, handle, url, role_id, start_date, end_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                person["person_id"],
                tlp["platform"],
                tlp["handle"],
                tlp["url"],
                tlp["role_id"],
                tlp.get("start_date"),
                tlp.get("end_date")
            ))

    conn.commit()
    conn.close()
    print(f"Exported registry to SQLite: {db_path}")

if __name__ == "__main__":
    compile_registry()
