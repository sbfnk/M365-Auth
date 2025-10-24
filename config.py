# Default configuration for M365 OAuth2 authentication
# Copy this file to ~/.config/m365auth/config.py to customize

# Thunderbird's public client ID (works for personal Microsoft accounts)
ClientId = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

# Client secret (can be empty for public clients)
ClientSecret = ""

# Optionally specify a tenant-specific authority URL for single-tenant apps:
# Authority = "https://login.microsoftonline.com/XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX/"
Authority = None

# OAuth2 redirect URI configuration
# This must match what's configured in your Azure app registration
RedirectUri = "https://localhost:7598/"
RedirectPort = 7598
UseHttps = True  # Set to False to use HTTP instead of HTTPS

# Profile-based scopes - use with --profile argument
# Azure AD doesn't allow mixing scopes from different resources in one token
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
    }
}

# Default profile if --profile not specified (for backward compatibility)
# You can also set Scopes directly instead of using profiles
Scopes = Profiles['mail']['scopes']
