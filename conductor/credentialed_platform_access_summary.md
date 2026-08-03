# Credentialed Platform Access Readiness

Generated: 2026-08-03T06:35:03+00:00

## Summary

- `selected_sources`: 849
- `actionable_configuration_fault_count`: 0
- `credential_hygiene_fault_count`: 0

## Platform status

- `facebook`: {'api_disabled_manual_seed_path': 326}
- `instagram`: {'api_disabled_manual_seed_path': 183}
- `linkedin`: {'api_disabled_manual_seed_path': 258}
- `threads`: {'api_disabled_manual_seed_path': 3}
- `x`: {'api_disabled_public_or_seed_path': 79}

## Policy

- Disabled live API gates are report-only states and must not open blocker issues.
- Enabled live API gates with missing required secrets are actionable configuration faults.
- Registered-but-unseeded credentialed accounts are not described as archived until records exist.
- Ordinary password environment variables are forbidden; use platform-issued read tokens or authorised exports.
