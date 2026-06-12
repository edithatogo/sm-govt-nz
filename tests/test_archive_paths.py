from pathlib import Path

from src.source_inventory import load_source_inventory


def test_raw_archive_roots_exist_for_all_source_contracts():
    inventory = load_source_inventory()

    for contract in inventory["contracts"]:
        template = contract["raw_path_template"]
        root = template.split("/{yyyy_mm}/", maxsplit=1)[0]
        assert Path(root).is_dir(), f"Missing raw archive root for {contract['id']}: {root}"


def test_normalized_archive_roots_exist_for_all_source_contracts():
    inventory = load_source_inventory()

    for contract in inventory["contracts"]:
        template = contract["normalized_path_template"]
        root = template.split("/{yyyy_mm}", maxsplit=1)[0]
        assert Path(root).is_dir(), f"Missing normalized archive root for {contract['id']}: {root}"
