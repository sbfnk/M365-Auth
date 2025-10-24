# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

M365-Auth is a Python-based OAuth2 authentication helper for connecting mail clients (like OfflineIMAP and msmtp) to Microsoft 365 / Exchange Online mailboxes. It handles the OAuth2 flow to obtain and refresh access tokens for IMAP and SMTP access.

Uses XDG Base Directory specification (via platformdirs) for cross-platform config and cache storage.

## Architecture

The codebase consists of three main components:

1. **config.py** - Configuration template containing:
   - `ClientId`: Azure AD app registration client ID (defaults to Thunderbird's public client ID)
   - `ClientSecret`: Optional client secret (can be empty for public clients)
   - `Authority`: Optional tenant-specific authority URL (defaults to `/common` multi-tenant)
   - `RedirectUri`: OAuth2 redirect URI (defaults to `https://localhost:7598/`)
   - `RedirectPort`: Local server port for OAuth callback (defaults to 7598)
   - `UseHttps`: Whether to use HTTPS or HTTP for local server (defaults to True)
   - `Profiles`: Profile-based scopes (`mail` and `calendar` profiles)
   - `Scopes`: Default OAuth2 scopes (defaults to `mail` profile)
   - Users can customize by copying to `~/.config/m365auth/config.py`

2. **get-token** - Interactive OAuth2 authorization flow:
   - Loads config from `~/.config/m365auth/config.py` (falls back to default `config.py`)
   - Creates MSAL `ConfidentialClientApplication` instance
   - Supports `--profile` argument to select scope profile (`mail` or `calendar`)
   - Launches local server on configured port (default: 7598) with optional HTTPS
   - HTTPS mode: auto-generates self-signed SSL cert cached in `~/.cache/m365auth/`
   - HTTP mode: uses plain HTTP (set `UseHttps = False` in config)
   - Opens browser to Microsoft login page
   - Handles OAuth2 redirect and exchanges authorization code for tokens
   - Stores refresh token in OS keychain (secure, encrypted)
   - Prints access token to stdout (not persisted to disk)
   - Falls back to manual URL entry for SSH/headless scenarios

3. **refresh-token** - Token refresh script:
   - Loads config from XDG config dir (same as get-token)
   - Reads existing refresh token from OS keychain
   - Uses MSAL to exchange refresh token for new access/refresh token pair
   - Updates refresh token in keychain (tokens rotate on each use)
   - Prints access token to stdout only (never persisted for security)
   - Designed to be called repeatedly by mail clients via passwordeval/PassCmd

4. **get-refresh-token** - Helper for OfflineIMAP:
   - Retrieves refresh token from OS keychain
   - Prints refresh token to stdout
   - Used by OfflineIMAP's `oauth2_refresh_token` field

## Key Dependencies

- **msal**: Microsoft Authentication Library for Python - handles OAuth2/OIDC flows
- **platformdirs**: Cross-platform XDG directory support
- **cryptography**: Self-signed SSL certificate generation
- **keyring**: Secure token storage using OS keychain (macOS Keychain, Linux Secret Service, Windows Credential Locker)

## Azure App Registration Setup

For organizational use or when Thunderbird's public client doesn't work, you can create your own Azure AD app registration:

### 1. Create App Registration in Azure Portal
1. Go to https://entra.microsoft.com or https://portal.azure.com
2. Navigate to: **Azure Active Directory** → **App registrations** → **New registration**
3. Configure:
   - **Name**: "M365-Auth IMAP/SMTP/Calendar Access" (or your choice)
   - **Supported account types**:
     - "Accounts in this organizational directory only" (single-tenant, recommended)
     - OR "Accounts in any organizational directory" (multi-tenant)
   - **Redirect URI**: Web → Enter your redirect URI (see config options below)
   - Click "Register"

### 2. Configure Authentication
1. In your app registration, go to **Authentication**
2. Under "Web" platform, add redirect URI(s):
   - Default: `https://localhost:7598/`
   - Or customize via config (see Redirect URI Configuration below)
3. Click **Save**

### 3. Add API Permissions
1. Go to **API permissions** → **Add a permission**
2. For email access:
   - Select **"Office 365 Exchange Online"** (or "APIs my organization uses")
   - Choose **Delegated permissions**
   - Add: `IMAP.AccessAsUser.All`, `SMTP.Send`
3. For calendar access:
   - Click **Add a permission** again → **Microsoft Graph**
   - Choose **Delegated permissions**
   - Add: `Calendars.ReadWrite`, `offline_access`
4. Click **Grant admin consent** (or request IT to grant consent)

### 4. Copy Configuration Values
- **Application (client) ID**: Copy from Overview page
- **Directory (tenant) ID**: Copy from Overview page (for single-tenant apps)

### 5. Customize Local Config
```bash
mkdir -p ~/.config/m365auth
cp config.py ~/.config/m365auth/config.py
# Edit ~/.config/m365auth/config.py with your values:
```

**Required changes:**
```python
ClientId = "YOUR-CLIENT-ID-FROM-AZURE"
Authority = "https://login.microsoftonline.com/YOUR-TENANT-ID/"  # For single-tenant
```

**Optional redirect URI customization:**
```python
# Example: Use HTTP on port 4999 with /getToken path
RedirectUri = "http://localhost:4999/getToken"
RedirectPort = 4999
UseHttps = False

# Make sure this matches what you configured in Azure app registration!
```

## Common Commands

### Initial Setup
```bash
pip install -r requirements.txt
# Optionally customize: mkdir -p ~/.config/m365auth && cp config.py ~/.config/m365auth/
get-token  # Interactive OAuth flow to obtain initial refresh token
```

### Refresh Access Token
```bash
refresh-token  # Refreshes tokens and prints access token (default: mail profile)
```

### Using Calendar Profile
```bash
get-token --profile calendar  # Get calendar access token
refresh-token --profile calendar  # Refresh calendar token
```

Note: Each profile maintains its own separate refresh token in the OS keychain.

### Installation to PATH
```bash
# Make scripts executable and copy to a directory in PATH
chmod +x get-token refresh-token get-refresh-token
cp get-token refresh-token get-refresh-token ~/.local/bin/  # or /usr/local/bin
```

## Directory Structure

- **Config**: `~/.config/m365auth/config.py` (Linux/XDG) or platform equivalent
- **Cache**: `~/.cache/m365auth/` (Linux/XDG) or platform equivalent
  - `server.key`, `server.cert` - Auto-generated self-signed SSL certificates
- **Keychain**: OS-native secure storage (macOS Keychain, GNOME Keyring, Windows Credential Locker)
  - `refresh_token` - OAuth2 refresh token (encrypted by OS)

## Security Model

- **Refresh tokens**: Stored in OS keychain (encrypted, secure)
- **Access tokens**: Never persisted to disk - only printed to stdout and held in memory by mail client
- **Benefit**: Even with filesystem access, attackers cannot obtain valid credentials without also accessing the OS keychain

## Integration Notes

- **OfflineIMAP**:
  ```ini
  auth_mechanisms = XOAUTH2
  oauth2_refresh_token_eval = get-refresh-token
  # Or use the refresh token directly:
  # oauth2_refresh_token = <output of get-refresh-token>
  ```
- **msmtp**:
  ```ini
  passwordeval "refresh-token"
  ```
- **mbsync/isync**:
  ```
  PassCmd "refresh-token"
  ```
- **SSH Usage**: When `SSH_CONNECTION` env var is set, `get-token` skips local server and prompts for manual URL entry
- **Tenant Support**: Copy config.py to `~/.config/m365auth/` and set tenant-specific `Authority` URL for single-tenant apps

## Python Environment

- Compatible with Python 3.6+
- Scripts use `#!/usr/bin/env python3` shebang for portability
