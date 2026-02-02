# Snow-Utils Common

Shared utilities for snow-utils skills.

## Modules

- `network_presets` - IP collection utilities (local IP, GitHub Actions, Google IPs)
- `snow_common` - Snowflake CLI wrappers
- `check_setup` - Infrastructure pre-flight checks

## Usage

Add as dependency in skill's pyproject.toml:

```toml
dependencies = [
    "snow-utils-common @ file:///${PROJECT_ROOT}/../common",
]
```

Then import:

```python
from snow_utils_common import collect_ipv4_cidrs, run_snow_sql
```
