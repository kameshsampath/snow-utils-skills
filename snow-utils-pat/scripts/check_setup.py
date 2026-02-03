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
Pre-flight check for snow-utils infrastructure.

Checks if SNOW_UTILS_DB and SA_ROLE exist.

Behavior:
  - TTY (terminal): Interactive prompts via click.confirm()
  - Non-TTY (CoCo/pipe): Outputs status, exits - CoCo handles prompts via ask_user_question

Exit codes:
  0 - Infrastructure ready
  1 - Infrastructure missing (setup needed)
  2 - Error during check
  3 - Setup needed, awaiting confirmation (non-TTY mode)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import click

DEFAULT_ROLE = "DEMO_ACCESS"
DEFAULT_DB = "SNOW_UTILS"


def get_demo_context() -> str:
    """Get project context from current directory name."""
    cwd = Path.cwd().name
    # Convert to uppercase, replace hyphens with underscores
    return cwd.upper().replace("-", "_")


def is_interactive() -> bool:
    """Check if running in interactive terminal (TTY)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def run_sql(query: str) -> list | None:
    """Execute SQL and return parsed JSON result. Uses active connection from env."""
    cmd = ["snow", "sql", "--query", query, "--format", "json"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None

    if result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
    return None


def check_database_exists(db_name: str) -> bool:
    """Check if a database exists."""
    try:
        result = run_sql(f"SHOW DATABASES LIKE '{db_name}'")
        return result is not None and len(result) > 0
    except Exception:
        return False


def check_role_exists(role_name: str) -> bool:
    """Check if a role exists."""
    try:
        result = run_sql(f"SHOW ROLES LIKE '{role_name}'")
        return result is not None and len(result) > 0
    except Exception:
        return False


def check_user_has_role(role_name: str) -> bool:
    """Check if current user has the specified role granted."""
    try:
        result = run_sql("SELECT CURRENT_AVAILABLE_ROLES() AS roles")
        if result and len(result) > 0:
            roles_str = result[0].get("ROLES", "[]")
            roles = json.loads(roles_str) if isinstance(roles_str, str) else roles_str
            return role_name.upper() in [r.upper() for r in roles]
    except Exception:
        pass
    return False


def run_setup(
    sa_role: str, db_name: str, user: str, admin_role: str, script_dir: Path
) -> bool:
    """Run the setup script with the specified admin role."""
    setup_sql = script_dir / "snow-utils-setup.sql"
    if not setup_sql.exists():
        click.echo(click.style(f"Setup script not found: {setup_sql}", fg="red"))
        return False

    click.echo(f"\nRunning setup with {admin_role}...")
    click.echo(f"  SA_ROLE: {sa_role}")
    click.echo(f"  SNOW_UTILS_DB: {db_name}")
    click.echo(f"  SNOWFLAKE_USER: {user}")
    click.echo(f"  SA_ADMIN_ROLE: {admin_role}")
    click.echo()

    env = os.environ.copy()
    env["SA_ROLE"] = sa_role.upper()
    env["SNOW_UTILS_DB"] = db_name.upper()
    env["SNOWFLAKE_USER"] = user.upper()
    env["SA_ADMIN_ROLE"] = admin_role.upper()

    cmd = [
        "snow",
        "sql",
        "-f",
        str(setup_sql),
        "--enable-templating",
        "ALL",
        "--role",
        admin_role.upper(),
    ]

    result = subprocess.run(cmd, env=env, capture_output=False)

    if result.returncode == 0:
        click.echo(click.style("\n✓ Setup complete!", fg="green"))
        return True
    else:
        click.echo(click.style("\n✗ Setup failed", fg="red"))
        return False


@click.command()
@click.option(
    "--role",
    "-r",
    envvar="SA_ROLE",
    default=None,
    help="SA Role name (or set SA_ROLE env var)",
)
@click.option(
    "--db",
    "-d",
    envvar="SNOW_UTILS_DB",
    default=None,
    help="Database name (or set SNOW_UTILS_DB env var)",
)
@click.option(
    "--user",
    "-u",
    envvar="SNOWFLAKE_USER",
    default=None,
    help="Snowflake user (or set SNOWFLAKE_USER env var)",
)
@click.option(
    "--setup",
    is_flag=True,
    help="Run setup if infrastructure missing (requires SA_ADMIN_ROLE)",
)
@click.option(
    "--confirmed",
    is_flag=True,
    hidden=True,
    help="User confirmed setup (set by CoCo after ask_user_question)",
)
@click.option(
    "--admin-role",
    "-a",
    envvar="SA_ADMIN_ROLE",
    default=None,
    help="Admin role for setup (or set SA_ADMIN_ROLE env var)",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["text", "json"]),
    default="text",
    help="Output format",
)
def check(
    role: str | None,
    db: str | None,
    user: str | None,
    setup: bool,
    confirmed: bool,
    admin_role: str | None,
    output: str,
):
    """Check if snow-utils infrastructure is set up.

    \b
    Behavior:
      - Terminal (TTY): Interactive prompts for confirmation
      - CoCo/pipe (non-TTY): Outputs status, CoCo handles prompts

    \b
    Exit codes:
      0 - Infrastructure ready
      1 - Infrastructure missing
      2 - Error during check
      3 - Setup needed, awaiting confirmation (non-TTY only)

    \b
    Examples:
      # Check status
      check_setup.py

      # Check and setup (interactive prompt in terminal)
      check_setup.py --setup

      # JSON output for CoCo
      check_setup.py --output json
    """
    script_dir = Path(__file__).parent
    interactive = is_interactive()

    # Build defaults from project context (current directory)
    user = user or os.environ.get("SNOWFLAKE_USER", "").upper()
    project_context = get_demo_context()

    if project_context:
        default_role = f"{project_context}_ACCESS"
        default_service_user = f"{project_context}_RUNNER"
        default_db = f"{user}_SNOW_UTILS" if user else "SNOW_UTILS"
    elif user:
        default_role = f"{user}_ACCESS"
        default_service_user = f"{user}_RUNNER"
        default_db = f"{user}_SNOW_UTILS"
    else:
        default_role = DEFAULT_ROLE
        default_service_user = "DEMO_RUNNER"
        default_db = DEFAULT_DB

    # Default admin role to ACCOUNTADMIN if not provided
    admin_role = admin_role or "ACCOUNTADMIN"

    # Use provided values or defaults (always uppercase for Snowflake)
    role = (role or default_role).upper()
    db = (db or default_db).upper()

    # Check infrastructure
    db_exists = check_database_exists(db)
    role_exists = check_role_exists(role)
    user_has_role = check_user_has_role(role) if role_exists else False
    ready = db_exists and role_exists

    # Build result
    result = {
        "ready": ready,
        "role": role,
        "role_exists": role_exists,
        "database": db,
        "database_exists": db_exists,
        "user_has_role": user_has_role,
        "user": user,
        "defaults": {
            "role": default_role,
            "service_user": default_service_user,
            "database": default_db,
            "admin_role": admin_role,
        },
        "setup_command": f"check_setup.py --setup --role {role} --db {db} --user {user} --admin-role {admin_role}",
    }

    if output == "json":
        click.echo(json.dumps(result, indent=2))
        sys.exit(0 if ready else 1)

    # Text output
    click.echo("Snow-utils infrastructure check\n")
    if user:
        click.echo(f"Detected user: {user}")
    click.echo(f"  SA_ROLE: {role}")
    click.echo(f"  SA_USER (default): {default_service_user}")
    click.echo(f"  SNOW_UTILS_DB: {db}")
    click.echo(f"  SA_ADMIN_ROLE: {admin_role}\n")

    if ready:
        click.echo(click.style("✓ Infrastructure ready", fg="green"))
        click.echo(f"  Database: {db}")
        click.echo(f"  Role: {role}")

        if not user_has_role:
            click.echo(
                click.style(
                    f"\n⚠ Note: You don't have {role} granted to your user.",
                    fg="yellow",
                )
            )
            click.echo(f'  Run: snow sql -q "GRANT ROLE {role} TO USER {user}"')

        sys.exit(0)

    # Not ready
    click.echo(click.style("⚠ Infrastructure not ready", fg="yellow"))
    if not db_exists:
        click.echo(f"  ✗ Database {db} does not exist")
    else:
        click.echo(f"  ✓ Database {db} exists")

    if not role_exists:
        click.echo(f"  ✗ Role {role} does not exist")
    else:
        click.echo(f"  ✓ Role {role} exists")

    # Setup requested?
    if setup:
        if not user:
            click.echo(
                click.style("\n✗ Cannot run setup: SNOWFLAKE_USER not set", fg="red")
            )
            sys.exit(2)

        # admin_role is already defaulted to ACCOUNTADMIN above

        # admin_role is already uppercase from default

        # Show what will be created
        click.echo(f"\nSetup will create:")
        click.echo(f"  - Role: {role}")
        click.echo(f"  - Database: {db}")
        click.echo(f"  - Schemas: {db}.NETWORKS, {db}.POLICIES")
        click.echo(f"  - Grant {role} to user {user}")
        click.echo(f"\nUsing admin role: {admin_role}")

        if interactive:
            # Terminal - use click.confirm()
            if not click.confirm("\nProceed with setup?", default=True):
                click.echo("Setup cancelled.")
                sys.exit(1)
            success = run_setup(role, db, user, admin_role, script_dir)
            sys.exit(0 if success else 1)
        elif confirmed:
            # Non-TTY but user confirmed via CoCo
            success = run_setup(role, db, user, admin_role, script_dir)
            sys.exit(0 if success else 1)
        else:
            # Non-TTY (CoCo) - exit with code 3, CoCo will prompt user
            click.echo("\n[Non-interactive mode] Awaiting confirmation...")
            click.echo(f"CoCo: Run with --confirmed after user approves")
            sys.exit(3)

    # No --setup flag, provide instructions
    click.echo(f"\nTo run setup:")
    click.echo(f"  check_setup.py --setup --admin-role ACCOUNTADMIN")
    click.echo(f"\nOr manually:")
    click.echo(
        f"  snow sql -f snow-utils-setup.sql --enable-templating ALL --role <SA_ADMIN_ROLE>"
    )
    sys.exit(1)


if __name__ == "__main__":
    check()
