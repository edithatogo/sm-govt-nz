# Credentialed Platform Access Readiness

Generated: 2026-07-13T06:46:01+00:00

## Summary

- `selected_sources`: 843
- `actionable_configuration_fault_count`: 0

## Platform status

- `facebook`: {'api_disabled_manual_seed_path': 322}
- `instagram`: {'api_disabled_manual_seed_path': 182}
- `linkedin`: {'api_disabled_manual_seed_path': 257}
- `threads`: {'api_enabled_ready': 3}
- `x`: {'api_disabled_public_or_seed_path': 79}

## Policy

- Disabled live API gates are report-only states and must not open blocker issues.
- Enabled live API gates with missing required secrets are actionable configuration faults.
- Registered-but-unseeded credentialed accounts are not described as archived until records exist.
