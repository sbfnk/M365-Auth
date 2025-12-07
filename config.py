# OAuth client configuration for Microsoft 365 IMAP/SMTP.
#
# By default use Thunderbird's public client ID. This app is already
# known to many tenants and usually has the right permissions.
#
# To use Thunderbird set-up:
#     * keep ClientId as-is
#     * leave ClientSecret empty
# When using other app registrations the config might differ slightly (like
# using client secret).

ClientId = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

# Only set a value if you registered an own Azure AD app with a client secret.
ClientSecret = ""

# Scopes requested from Microsoft 365.
# - IMAP.AccessAsUser.All : IMAP access
# - SMTP.Send             : sending mail via SMTP
# - offline_access        : allows us to receive a refresh token
Scopes = [
    "https://outlook.office.com/IMAP.AccessAsUser.All",
    "https://outlook.office.com/SMTP.Send",
    "offline_access",
]

# Files used to store tokens created during OAuth flow by the scripts.
RefreshTokenFileName = "imap_smtp_refresh_token"
AccessTokenFileName = "imap_smtp_access_token"

# Optional: tenant-specific authority, e.g.
# Authority = "https://login.microsoftonline.com/<your-tenant-id>/"
# If left as None, MSAL uses the "common" endpoint.
Authority = None