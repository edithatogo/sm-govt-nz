# Registry Gap Analysis Skill

Purpose: regenerate and inspect cross-platform social coverage for NZ public-sector agencies.

Commands:

```powershell
python scripts/gap_analyzer.py --registry registry/agencies.json --output registry/gap_analysis.json
pytest -q tests/test_gap_analyzer.py
```

Expected output: `registry/gap_analysis.json` with platform coverage, open-network coverage, proprietary-without-open gaps, and deactivated profile records.