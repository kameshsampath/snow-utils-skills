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
-- Creates the SA role and database. SA_ADMIN_ROLE owns all objects.
--
-- Environment Variables (from .env):
--   SA_ROLE        - Role for service account (PAT role restriction)
--   SNOW_UTILS_DB  - Database for snow-utils objects
--   SNOWFLAKE_USER - Current user (will be granted SA_ROLE)
--   SA_ADMIN_ROLE  - Admin role that owns DB and runs setup (e.g., ACCOUNTADMIN)
--
-- Security Model:
--   SA_ADMIN_ROLE owns database and schemas, handles all operations:
--     - Database/schema ownership
--     - CREATE USER (service accounts)
--     - CREATE NETWORK RULE/POLICY
--     - CREATE AUTHENTICATION POLICY
--     - CREATE EXTERNAL VOLUME
--     - ALTER USER (policy assignments)
--
--   SA_ROLE is for PAT role restriction only (what the service account can do).
--   Grant SA_ROLE additional privileges as needed for specific use cases.
--
-- Prerequisites:
--   - Must be run by SA_ADMIN_ROLE (default: ACCOUNTADMIN)
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
