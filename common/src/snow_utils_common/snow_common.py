#!/usr/bin/env python3
# Copyright 2026 Kamesh Sampath
# Generated with Cortex Code
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Common utilities for Snowflake CLI tools.

Shared functionality for snow CLI wrapper functions and options.
"""

import json
import os
import re
import subprocess
from dataclasses import dataclass

import click


@dataclass
class SnowCLIOptions:
    """Options for snow CLI commands."""

    verbose: bool = False
    debug: bool = False
    mask_sensitive: bool = True
    connection: str | None = None
    force_user_connection: bool = False

    def get_flags(self) -> list[str]:
        """Get CLI flags based on options.

        If SA_PAT is set and force_user_connection is False, uses temporary
        connection mode with SA credentials.
        Otherwise, uses named connection from SNOWFLAKE_DEFAULT_CONNECTION_NAME.

        Note: PAT token is passed via SNOWFLAKE_PASSWORD env var (see get_env()),
        not on command line, to avoid exposing secrets in process list.
        """
        flags = []
        sa_pat = os.environ.get("SA_PAT")
        if sa_pat and not self.force_user_connection:
            sa_user = os.environ.get("SA_USER")
            account = os.environ.get("SNOWFLAKE_ACCOUNT")
            sa_role = os.environ.get("SA_ROLE")
            if sa_user and account:
                flags.extend(
                    [
                        "--temporary-connection",
                        "--account",
                        account,
                        "--user",
                        sa_user,
                        "--authenticator",
                        "PROGRAMMATIC_ACCESS_TOKEN",
                    ]
                )
                if sa_role:
                    flags.extend(["--role", sa_role])
            else:
                click.echo(
                    "Warning: SA_PAT set but SA_USER or SNOWFLAKE_ACCOUNT missing",
                    err=True,
                )
                conn = self.connection or os.environ.get(
                    "SNOWFLAKE_DEFAULT_CONNECTION_NAME"
                )
                if conn:
                    flags.extend(["-c", conn])
        else:
            conn = self.connection or os.environ.get(
                "SNOWFLAKE_DEFAULT_CONNECTION_NAME"
            )
            if conn:
                flags.extend(["-c", conn])
        if self.debug:
            flags.append("--debug")
        elif self.verbose:
            flags.append("--verbose")
        return flags

    def get_env(self) -> dict[str, str]:
        """Get environment variables for subprocess.

        If SA_PAT is set and force_user_connection is False, includes
        SNOWFLAKE_PASSWORD with the token.
        This keeps the token out of the command line (security).
        """
        env = dict(os.environ)
        sa_pat = os.environ.get("SA_PAT")
        if sa_pat and self.uses_sa_credentials() and not self.force_user_connection:
            env["SNOWFLAKE_PASSWORD"] = sa_pat
        return env

    def uses_sa_credentials(self) -> bool:
        """Check if SA credentials will be used."""
        if self.force_user_connection:
            return False
        sa_pat = os.environ.get("SA_PAT")
        sa_user = os.environ.get("SA_USER")
        account = os.environ.get("SNOWFLAKE_ACCOUNT")
        return bool(sa_pat and sa_user and account)


_snow_cli_options = SnowCLIOptions()


def set_force_user_connection(force: bool) -> None:
    """Set whether to force using user's connection (bypass SA credentials).

    Use this during PAT creation when SA_PAT doesn't exist yet but may
    be present as a stale value in .env.
    """
    _snow_cli_options.force_user_connection = force


def mask_aws_account_id(value: str) -> str:
    """Mask AWS account ID: 123456789012 -> 1234****9012"""
    if len(value) == 12 and value.isdigit():
        return f"{value[:4]}****{value[-4:]}"
    return value


def mask_ip_address(value: str) -> str:
    """Mask IP address: 192.168.1.100 -> 192.168.***.***"""
    parts = value.replace("/32", "").split(".")
    if len(parts) == 4:
        masked = f"{parts[0]}.{parts[1]}.***.***"
        if "/32" in value:
            masked += "/32"
        return masked
    return value


def mask_external_id(value: str) -> str:
    """Mask external ID: abc123xyz -> abc***xyz"""
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}{'*' * (len(value) - 6)}{value[-3:]}"


def mask_arn(value: str) -> str:
    """Mask ARN account ID portion."""
    pattern = r"(arn:aws:[^:]+:[^:]*:)(\d{12})(:.+)"
    match = re.match(pattern, value)
    if match:
        return f"{match.group(1)}{mask_aws_account_id(match.group(2))}{match.group(3)}"
    return value


def mask_sensitive_string(value: str, mask_type: str = "auto") -> str:
    """Mask a sensitive string based on type or auto-detect."""
    if not _snow_cli_options.mask_sensitive:
        return value

    is_account_id = mask_type == "aws_account_id" or (
        mask_type == "auto" and len(value) == 12 and value.isdigit()
    )
    if is_account_id:
        return mask_aws_account_id(value)
    is_ip = mask_type == "ip" or (
        mask_type == "auto" and re.match(r"^\d+\.\d+\.\d+\.\d+(/\d+)?$", value)
    )
    if is_ip:
        return mask_ip_address(value)
    elif mask_type == "arn" or (mask_type == "auto" and value.startswith("arn:aws:")):
        return mask_arn(value)
    elif mask_type == "external_id":
        return mask_external_id(value)
    return value


def mask_json_sensitive(
    data: dict | list, sensitive_keys: list[str] | None = None
) -> dict | list:
    """Recursively mask sensitive values in JSON data."""
    if not _snow_cli_options.mask_sensitive:
        return data

    if sensitive_keys is None:
        sensitive_keys = ["AWS", "arn", "account", "external", "ip", "address"]

    def should_mask_key(key: str) -> bool:
        key_lower = key.lower()
        return any(sk.lower() in key_lower for sk in sensitive_keys)

    def mask_value(key: str, value):
        if isinstance(value, str):
            if "arn:aws:" in value:
                return mask_arn(value)
            elif re.match(r"^\d{12}$", value):
                return mask_aws_account_id(value)
            elif re.match(r"^\d+\.\d+\.\d+\.\d+(/\d+)?$", value):
                return mask_ip_address(value)
            elif should_mask_key(key) and len(value) > 6:
                return mask_external_id(value)
        return value

    def recurse(obj, parent_key=""):
        if isinstance(obj, dict):
            return {k: recurse(v, k) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [recurse(item, parent_key) for item in obj]
        else:
            return mask_value(parent_key, obj)

    return recurse(data)


def set_masking(enabled: bool) -> None:
    """Enable or disable sensitive value masking."""
    global _snow_cli_options
    _snow_cli_options.mask_sensitive = enabled


def is_masking_enabled() -> bool:
    """Check if masking is enabled."""
    return _snow_cli_options.mask_sensitive


def set_snow_cli_options(
    verbose: bool = False,
    debug: bool = False,
    mask_sensitive: bool = True,
    connection: str | None = None,
) -> None:
    """Set global snow CLI options."""
    global _snow_cli_options
    _snow_cli_options = SnowCLIOptions(
        verbose=verbose,
        debug=debug,
        mask_sensitive=mask_sensitive,
        connection=connection,
    )


def get_snow_cli_options() -> SnowCLIOptions:
    """Get current snow CLI options."""
    return _snow_cli_options


def run_snow_sql(
    query: str, *, format: str = "json", check: bool = True
) -> dict | list | None:
    """Execute a snow sql command and return parsed JSON output."""
    cmd = [
        "snow",
        "sql",
        *_snow_cli_options.get_flags(),
        "--query",
        query,
        "--format",
        format,
    ]

    if _snow_cli_options.debug:
        click.echo(f"[DEBUG] Running: {' '.join(cmd)}")

    result = subprocess.run(
        cmd, capture_output=True, text=True, env=_snow_cli_options.get_env()
    )

    if _snow_cli_options.debug and result.stderr:
        click.echo(f"[DEBUG] stderr: {result.stderr}")

    if check and result.returncode != 0:
        raise click.ClickException(f"snow sql failed: {result.stderr}")

    if format == "json" and result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
    return None


def run_snow_sql_stdin(sql: str, *, check: bool = True) -> subprocess.CompletedProcess:
    """Execute multi-statement SQL via stdin."""
    cmd = ["snow", "sql", *_snow_cli_options.get_flags(), "--stdin"]

    if _snow_cli_options.debug:
        click.echo(f"[DEBUG] Running: {' '.join(cmd)}")
        click.echo(f"[DEBUG] SQL:\n{sql}")

    result = subprocess.run(
        cmd, input=sql, capture_output=True, text=True, env=_snow_cli_options.get_env()
    )

    if _snow_cli_options.debug and result.stderr:
        click.echo(f"[DEBUG] stderr: {result.stderr}")
    if _snow_cli_options.debug and result.stdout:
        click.echo(f"[DEBUG] stdout: {result.stdout}")

    if check and result.returncode != 0:
        raise click.ClickException(f"snow sql failed: {result.stderr}")

    return result
