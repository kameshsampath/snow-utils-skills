-- Copyright 2026 Kamesh Sampath
-- Generated with Cortex Code
--
-- Licensed under the Apache License, Version 2.0 (the "License");
-- you may not use this file except in compliance with the License.
-- You may obtain a copy of the License at
--
--     http://www.apache.org/licenses/LICENSE-2.0
--
-- Unless required by applicable law or agreed to in writing, software
-- distributed under the License is distributed on an "AS IS" BASIS,
-- WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
-- See the License for the specific language governing permissions and
-- limitations under the License.

--!jinja

-- =============================================================================
-- Snow-Utils Setup Script
-- =============================================================================
-- Creates shared infrastructure database and default SA role.
--
-- Environment Variables (from .env):
--   SA_ROLE        - Role for PAT restriction (demo-scoped, set per-demo)
--   SNOW_UTILS_DB  - Shared infra database for account-level objects
--   SNOWFLAKE_USER - Current user (will be granted SA_ROLE)
--   SA_ADMIN_ROLE  - Admin role that owns infra DB (e.g., ACCOUNTADMIN)
--
-- Architecture:
--   SNOW_UTILS_DB is shared infrastructure:
--     - NETWORKS schema: network rules for any demo
--     - POLICIES schema: auth policies for any demo
--     - Owned by SA_ADMIN_ROLE, used by all demos
--
--   SA_ADMIN_ROLE handles all privileged operations:
--     - Owns SNOW_UTILS_DB and schemas
--     - CREATE USER, NETWORK RULE/POLICY, AUTH POLICY, EXTERNAL VOLUME
--     - ALTER USER (policy assignments)
--
--   SA_ROLE is demo-scoped (set per-demo in .env):
--     - Restricts what PAT service accounts can access
--     - Demo setup grants SA_ROLE only demo-specific resources
--     - Example: SA_ROLE=HIRC_DUCKDB_DEMO_SA (access to demo tables only)
--
-- Usage:
--   snow sql -f snow-utils-setup.sql --enable-templating ALL --role <SA_ADMIN_ROLE>
-- =============================================================================

USE ROLE <% ctx.env.SA_ADMIN_ROLE %>;

-- =============================================================================
-- Step 1: Create SA Role (for PAT role restriction)
-- =============================================================================

CREATE ROLE IF NOT EXISTS <% ctx.env.SA_ROLE %>
    COMMENT = 'Role for service account PAT restriction';

-- =============================================================================
-- Step 2: Create Database and Schemas (owned by SA_ADMIN_ROLE)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS <% ctx.env.SNOW_UTILS_DB %>
    COMMENT = 'Database for snow-utils objects (network rules, policies, etc.)';

CREATE SCHEMA IF NOT EXISTS <% ctx.env.SNOW_UTILS_DB %>.NETWORKS
    COMMENT = 'Schema for network rules';
CREATE SCHEMA IF NOT EXISTS <% ctx.env.SNOW_UTILS_DB %>.POLICIES
    COMMENT = 'Schema for authentication policies';

-- =============================================================================
-- Step 3: Grant SA Role to Current User and SYSADMIN
-- =============================================================================

GRANT ROLE <% ctx.env.SA_ROLE %> TO USER <% ctx.env.SNOWFLAKE_USER %>;
GRANT ROLE <% ctx.env.SA_ROLE %> TO ROLE SYSADMIN;

-- =============================================================================
-- Verification
-- =============================================================================
-- SHOW GRANTS TO ROLE <% ctx.env.SA_ROLE %>;
-- SHOW GRANTS ON DATABASE <% ctx.env.SNOW_UTILS_DB %>;

SELECT 'Snow-utils setup complete. SA_ADMIN_ROLE <% ctx.env.SA_ADMIN_ROLE %> owns <% ctx.env.SNOW_UTILS_DB %>. SA_ROLE <% ctx.env.SA_ROLE %> granted to <% ctx.env.SNOWFLAKE_USER %>.' AS status;
