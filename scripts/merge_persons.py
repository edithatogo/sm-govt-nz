"""Merge separate person JSON files into a single registry/persons.json."""
import json
from pathlib import Path

def merge_persons(source_files: list[str], output_path: str = "registry/persons.json"):
    """Merge multiple person JSON arrays into one, deduplicating by person_id."""
    all_persons: dict[str, dict] = {}
    
    # Start with existing persons.json if it has content
    output_file = Path(output_path)
    if output_file.exists() and output_file.stat().st_size > 5:
        with open(output_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
            for person in existing:
                all_persons[person["person_id"]] = person
    
    # Merge from source files
    for source_path in source_files:
        src = Path(source_path)
        if not src.exists():
            print(f"Skipping {source_path} — file not found")
            continue
        with open(src, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error parsing {source_path}: {e}")
                continue
        for person in data:
            pid = person.get("person_id")
            if pid and pid not in all_persons:
                all_persons[pid] = person
                print(f"  Added {pid} ({person.get('full_name', '?')})")
            elif pid:
                print(f"  Skipped duplicate {pid}")
    
    # Write merged output
    merged = list(all_persons.values())
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    
    print(f"\nMerged {len(merged)} persons into {output_path}")

if __name__ == "__main__":
    merge_persons([
        "registry/persons_national.json",
        "registry/persons_labour.json",
        "registry/persons_minor.json",
        "registry/persons_leaders.json",
    ])
