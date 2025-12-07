from msal import ConfidentialClientApplication, SerializableTokenCache
import config
import sys
from pathlib import Path

# Set to False if you only want to refresh the token files without printing
# the access token (e.g. for periodic refresh jobs).
print_access_token = True

cache = SerializableTokenCache()

app = ConfidentialClientApplication(
    client_id=config.ClientId,
    client_credential=config.ClientSecret or None,
    token_cache=cache,
    authority=config.Authority,
)

refresh_path = Path(config.RefreshTokenFileName)
if not refresh_path.exists():
    sys.exit(
        f"Refresh token file {config.RefreshTokenFileName} not found. "
        "Run get_token.py first."
    )

old_refresh_token = refresh_path.read_text().strip()

# Request a new access token (and usually a new refresh token).
token = app.acquire_token_by_refresh_token(old_refresh_token, scopes=config.Scopes)

if "error" in token:
    print(token)
    sys.exit("Failed to get access token")

# Save the new refresh token if MSAL returned one; otherwise keep the old one.
new_refresh_token = token.get("refresh_token", old_refresh_token)
refresh_path.write_text(new_refresh_token)

with open(config.AccessTokenFileName, "w") as f:
    f.write(token["access_token"])

if print_access_token:
    # Printing the access token allows SMTP clients like msmtp to use this
    # script as password source (passwordeval).
    print(token["access_token"])