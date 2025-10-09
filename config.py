# Default configuration for M365-IMAP OAuth2 authentication
# Copy this file to ~/.config/m365-imap/config.py to customize

# Thunderbird's public client ID (works for personal Microsoft accounts)
ClientId = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

# Client secret (can be empty for public clients)
ClientSecret = ""

# OAuth2 scopes for IMAP and SMTP access
Scopes = ['https://outlook.office.com/IMAP.AccessAsUser.All','https://outlook.office.com/SMTP.Send']

# Optionally specify a tenant-specific authority URL for single-tenant apps:
# Authority = "https://login.microsoftonline.com/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/"
Authority = None
