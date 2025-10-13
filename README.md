# M365-Auth: OAuth2 Authentication for Microsoft 365

A Python-based OAuth2 authentication tool for Microsoft 365 services including IMAP, SMTP, and Calendar access. Works with any mail client or application that supports OAuth2 authentication.

**Based on the original [M365-IMAP](https://github.com/UvA-FNWI/M365-IMAP) by Gerrit Oomens, which itself was forked from [ag91/M365-IMAP](https://github.com/ag91/M365-IMAP).**

## Features

- **Universal OAuth2 support**: Works with any M365 service (mail, calendar, etc.)
- **Multiple profiles**: Separate token management for different services
- **Secure storage**: Tokens stored in OS keychain (macOS Keychain, GNOME Keyring, Windows Credential Locker)
- **Cross-platform**: Linux, macOS, Windows
- **Mail client support**: mbsync, msmtp, OfflineIMAP, and any OAuth2-compatible client
- **Python library**: Import and use in your own scripts
- **XDG compliant**: Follows XDG Base Directory specification

## Installation

```bash
git clone https://github.com/YOUR-USERNAME/M365-Auth
cd M365-Auth
pip install -e .
```

This installs the package and creates three commands:
- `get-token` - Interactive OAuth2 flow to obtain tokens
- `refresh-token` - Refresh and print access tokens
- `get-refresh-token` - Get refresh token from keychain (for OfflineIMAP)

## Quick Start

### Step 1: Get a Client ID

To connect to Azure AD for authentication, you need a client ID and optionally a client secret (an "app registration" in Azure AD).

**Understanding client secrets:** Confusingly, the client secret doesn't actually need to be secret for mail clients and desktop applications. Public clients (like mail clients) can't keep secrets anyway - anyone can decompile the app and extract them. That's why many public clients use empty secrets or publicly-known ones.

**Your options:**

#### Option 1: Create your own app registration (recommended)

This gives you full control and ensures you have all the permissions you need:

1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Click "New registration"
   - **Name**: Something like "My Mail Client" or "Personal M365 Tools"
   - **Supported account types**: Choose based on your account type
   - **Redirect URI**: Web → `https://localhost:7598`
3. After creation, copy the **Application (client) ID**
4. Go to "API permissions" → "Add a permission" → "Microsoft Graph" → "Delegated permissions"
5. Add the permissions you need (see API Permissions section below)
6. **Important**: If using a work/school account, you may need admin consent - click "Grant admin consent" or ask your IT admin

**Note**: The redirect URI is where Azure AD sends the user after authentication. We run a local HTTPS server on port 7598 to catch this redirect.

#### Option 2: Use a public client ID

Some applications publish their client IDs in their source code, which you can use. For example:

- **Thunderbird**: Available in their [source code](https://hg-edge.mozilla.org/comm-central/file/tip/mailnews/base/src/OAuth2Providers.sys.mjs#l186)
- **Other mail clients**: Check their public repositories or documentation

To find a public client ID:
1. Look in the application's source code repository
2. Search for files related to OAuth2 or Microsoft authentication
3. Look for strings that match the format of Azure AD client IDs (typically 36-character GUIDs)

**Pros of using public client IDs:**
- No need to create your own app registration
- Often already approved by IT departments for common applications
- Works immediately for personal accounts

**Cons:**
- You don't control the permissions
- May not have calendar or other non-mail permissions
- Could theoretically be revoked by the original publisher
- You're using an ID intended for a different application

Whatever client ID you use, it needs to have been granted the appropriate permissions in your M365 tenant (for work/school accounts) or support the permissions you need (for personal accounts).

### Step 2: Configure

On first run, `get-token` will automatically create a default configuration file at `~/.config/m365auth/config.py`. You must edit this file to add your client ID:

```bash
# The config file will be created automatically on first run
# Edit it to add your client ID
nano ~/.config/m365auth/config.py
```

Set `ClientId = "your-client-id-here"` in the config file.

The default config includes two profiles:
- **mail**: `IMAP.AccessAsUser.All`, `SMTP.Send`
- **calendar**: `Calendars.ReadWrite`

### Step 3: Get Your Tokens

**Understanding OAuth2 tokens:** The OAuth2 flow gives you two types of tokens:
- **Refresh token**: Long-lived (months/years), used to get new access tokens. Stored securely in your OS keychain.
- **Access token**: Short-lived (~1 hour), used to actually access your mail/calendar. Never persisted to disk for security.

Mail clients need fresh access tokens frequently, so they call `refresh-token` which uses your stored refresh token to get a new access token each time.

**Get your initial tokens:**

```bash
# For mail clients (IMAP/SMTP)
get-token --profile mail

# For calendar access
get-token --profile calendar

# Over SSH with port forwarding
get-token --profile mail --server
```

**What happens:**
1. The script opens your browser to Microsoft's login page
2. You authenticate with your Microsoft account
3. Microsoft redirects to `https://localhost:7598` with an authorization code
4. The script exchanges this code for tokens using [Microsoft's MSAL library](https://docs.microsoft.com/en-us/azure/active-directory/develop/msal-overview)
5. The **refresh token** is stored in your OS keychain (encrypted, secure)
6. The **access token** is printed (but not saved - you don't need it, `refresh-token` will generate new ones)

**Security note:** The refresh token allows access to your full mailbox/calendar (depending on permissions), so it's stored in your system's secure keychain, not a plain file. Even if someone gets filesystem access, they can't use your credentials without also accessing your keychain.

## Usage Examples

### mbsync (isync)

```
IMAPAccount account
Host outlook.office365.com
User your.email@example.com
PassCmd "refresh-token --profile mail"
AuthMechs XOAUTH2
SSLType IMAPS
```

### msmtp

```
account myaccount
host smtp.office365.com
port 587
from your.email@example.com
user your.email@example.com
auth xoauth2
passwordeval "refresh-token --profile mail"
tls on
tls_starttls on
```

### OfflineIMAP

```ini
[Repository Remote]
type = IMAP
remotehost = outlook.office365.com
remoteuser = your.email@example.com
auth_mechanisms = XOAUTH2
oauth2_request_url = https://login.microsoftonline.com/common/oauth2/v2.0/token
oauth2_client_id = <your client ID>
oauth2_client_secret =
oauth2_refresh_token_eval = get-refresh-token --profile mail

# Optional: filter non-mail folders
folderfilter = lambda folder: not folder.startswith('Calendar') and not folder.startswith('Contacts')
```

### Python Scripts

```python
from m365auth import get_access_token

# Get access token for mail
token = get_access_token('mail')

# Get access token for calendar
token = get_access_token('calendar')

# Use with requests
headers = {'Authorization': f'Bearer {token}'}
response = requests.get('https://graph.microsoft.com/v1.0/me/calendar', headers=headers)
```

## API Permissions

Common Microsoft Graph delegated permissions:

**Mail:**
- `https://outlook.office.com/IMAP.AccessAsUser.All` - IMAP access
- `https://outlook.office.com/SMTP.Send` - SMTP sending

**Calendar:**
- `https://graph.microsoft.com/Calendars.ReadWrite` - Calendar read/write

**Other:**
- `https://graph.microsoft.com/Mail.ReadWrite` - Mail via Graph API
- `https://graph.microsoft.com/Calendars.Read` - Calendar read-only

Note: Azure AD doesn't allow mixing `outlook.office.com` and `graph.microsoft.com` scopes in one token. Use separate profiles for different resource types.

## Configuration

### Directory Structure

- **Config**: `~/.config/m365auth/config.py` (Linux) or platform equivalent
- **Cache**: `~/.cache/m365auth/` (Linux) or platform equivalent
  - Auto-generated SSL certificates for OAuth callback server
- **Keychain**: OS-native secure storage
  - Refresh tokens stored as `m365auth-{profile}`

### Custom Profiles

Edit `~/.config/m365auth/config.py`:

```python
Profiles = {
    'mail': {
        'scopes': [
            'https://outlook.office.com/IMAP.AccessAsUser.All',
            'https://outlook.office.com/SMTP.Send'
        ]
    },
    'calendar': {
        'scopes': [
            'https://graph.microsoft.com/Calendars.ReadWrite'
        ]
    },
    'custom': {
        'scopes': [
            # Your custom scopes here
        ]
    }
}
```

### Tenant-Specific Configuration

For single-tenant (work/school) accounts:

```python
Authority = "https://login.microsoftonline.com/YOUR-TENANT-ID/"
```

## Security

- **Refresh tokens**: Stored encrypted in OS keychain
- **Access tokens**: Never persisted to disk - only printed to stdout or held in memory
- **File fallback**: For headless environments, tokens stored in `~/.cache/m365auth/` with mode 600
- **Benefit**: Even with filesystem access, attackers need keychain access to get credentials

## SSH / Headless Usage

When running over SSH, the browser can't reach `localhost:7598` on the remote machine. Two options:

### Option 1: SSH Port Forwarding (recommended)

SSH port forwarding creates a tunnel so that `localhost:7598` on your local machine connects to `localhost:7598` on the remote machine.

**Step-by-step:**

```bash
# Step 1: On your local machine, connect with port forwarding
ssh -L 7598:localhost:7598 user@remote-host

# Step 2: On the remote machine (in the SSH session)
get-token --profile mail --server

# Step 3: The script will print a URL and open it in your local browser
# (The --server flag tells the script to start the HTTPS server even over SSH)

# Step 4: Authenticate in your browser
# The redirect to localhost:7598 will go through the SSH tunnel to the remote machine

# Step 5: Done! The token is stored in the remote machine's keychain
```

**How it works:**
- `-L 7598:localhost:7598` creates a tunnel from local port 7598 to remote port 7598
- When Microsoft redirects to `https://localhost:7598`, your browser connects to your local port 7598
- SSH forwards that connection through the tunnel to the remote machine
- The remote machine's OAuth server receives the authorization code

### Option 2: Manual URL Entry (for existing SSH sessions)

If you're already connected via SSH without port forwarding:

```bash
# On the remote machine
get-token --profile mail

# Script detects SSH (no --server flag) and skips starting the server
# It prints the OAuth URL and waits

# Open the URL in your local browser and authenticate
# Microsoft will redirect to https://localhost:7598/?code=...
# This will fail to load (that's expected!)

# Copy the entire error page URL from your browser
# Paste it back into the SSH terminal

# Done! The script extracts the code and completes authentication
```

**Note:** For headless servers with no browser access at all, you need to open the URL on any machine with a browser, then paste the redirect URL back to the server.

## Troubleshooting

**"No refresh token found"**
```bash
# Run get-token first to authenticate
get-token --profile mail
```

**"Cannot store in keychain"**
- File fallback is automatic
- Tokens stored in `~/.cache/m365auth/refresh_token_{profile}`
- On headless Linux, consider installing `gnome-keyring`

**"Permission denied" errors**
- Your Azure app needs the required API permissions
- Contact your IT admin to grant consent

**SSL certificate warnings**
- Normal for self-signed certificates on localhost
- Safe to click through during OAuth flow

## Contributing

Contributions welcome! This is a fork of the original [M365-IMAP](https://github.com/UvA-FNWI/M365-IMAP) project, extended to support multiple services beyond just IMAP.

## License

MIT License - see original [M365-IMAP](https://github.com/UvA-FNWI/M365-IMAP) repository.

## Credits

- Original implementation: [Gerrit Oomens](https://github.com/UvA-FNWI/M365-IMAP)
- Earlier fork: [ag91/M365-IMAP](https://github.com/ag91/M365-IMAP)
