import json
from pathlib import Path
from typing import Literal, TypedDict, cast


SourceHealth = Literal[
    "healthy",
    "degraded",
    "auth_required",
    "rate_limited",
    "blocked",
    "unavailable",
]


class SourceContract(TypedDict, total=False):
    id: str
    source_platform: str
    source_kind: str
    display_name: str
    account: str
    url: str
    access_method: str
    auth: str
    status: SourceHealth
    historical_cutoff: str
    seed_pages: list[str]
    subscription_sections: list[str]
    dedupe_keys: list[str]
    raw_path_template: str
    normalized_path_template: str
    rate_limit_policy: str
    archive_only_guarantee: str
    failure_modes: list[str]


class DatasetOutput(TypedDict):
    enabled: bool
    secret_requirements: list[str]
    artifacts: list[str]


class PhaseReviewContract(TypedDict):
    commit_after_each_task: bool
    review_after_each_phase: bool
    review_after_track: bool
    future_syndication_tracks: str


class SourceInventory(TypedDict):
    agency_id: str
    agency_name: str
    archive_only: bool
    contracts: list[SourceContract]
    dataset_outputs: dict[str, DatasetOutput]
    phase_review_contract: PhaseReviewContract


REQUIRED_CONTRACT_FIELDS = {
    "id",
    "source_platform",
    "source_kind",
    "display_name",
    "account",
    "url",
    "access_method",
    "auth",
    "status",
    "dedupe_keys",
    "raw_path_template",
    "normalized_path_template",
    "rate_limit_policy",
    "archive_only_guarantee",
    "failure_modes",
}

ALLOWED_HEALTH: set[str] = {
    "healthy",
    "degraded",
    "auth_required",
    "rate_limited",
    "blocked",
    "unavailable",
}


def load_source_inventory(
    path: str | Path = "config/courts-of-nz_sources.json",
) -> SourceInventory:
    inventory_path = Path(path)
    if not inventory_path.exists():
        raise FileNotFoundError(f"Source inventory not found at: {inventory_path}")

    with inventory_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    _validate_inventory(data)
    return cast(SourceInventory, data)


def _validate_inventory(data: object) -> None:
    if not isinstance(data, dict):
        raise ValueError("Source inventory must be a JSON object.")

    for field in ("agency_id", "agency_name", "archive_only", "contracts"):
        if field not in data:
            raise ValueError(f"Source inventory missing required field: {field}")

    if data["archive_only"] is not True:
        raise ValueError("Source inventory must be archive_only=true.")

    contracts = data["contracts"]
    if not isinstance(contracts, list) or not contracts:
        raise ValueError("Source inventory must contain at least one contract.")

    seen_ids: set[str] = set()
    for contract in contracts:
        _validate_contract(contract, seen_ids)

    outputs = data.get("dataset_outputs", {})
    if not isinstance(outputs, dict) or "hugging_face" not in outputs or "zenodo" not in outputs:
        raise ValueError("Source inventory must define Hugging Face and Zenodo dataset outputs.")

    review = data.get("phase_review_contract", {})
    if not isinstance(review, dict):
        raise ValueError("Source inventory phase_review_contract must be an object.")
    for field in ("commit_after_each_task", "review_after_each_phase", "review_after_track"):
        if review.get(field) is not True:
            raise ValueError(f"Source inventory phase_review_contract must set {field}=true.")


def _validate_contract(contract: object, seen_ids: set[str]) -> None:
    if not isinstance(contract, dict):
        raise ValueError("Each source contract must be a JSON object.")

    missing = REQUIRED_CONTRACT_FIELDS - set(contract)
    if missing:
        raise ValueError(f"Source contract missing required fields: {', '.join(sorted(missing))}")

    contract_id = str(contract["id"])
    if contract_id in seen_ids:
        raise ValueError(f"Duplicate source contract id: {contract_id}")
    seen_ids.add(contract_id)

    status = str(contract["status"])
    if status not in ALLOWED_HEALTH:
        raise ValueError(f"Invalid source health status for {contract_id}: {status}")

    for list_field in ("dedupe_keys", "failure_modes"):
        value = contract[list_field]
        if not isinstance(value, list) or not value:
            raise ValueError(f"Source contract {contract_id} must define non-empty {list_field}.")

    raw_template = str(contract["raw_path_template"])
    normalized_template = str(contract["normalized_path_template"])
    if "{yyyy_mm}" not in raw_template or "{record_id}" not in raw_template:
        raise ValueError(f"Source contract {contract_id} raw path must include yyyy_mm and record_id.")
    if "{yyyy_mm}" not in normalized_template:
        raise ValueError(f"Source contract {contract_id} normalized path must include yyyy_mm.")
