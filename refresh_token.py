from msal import ConfidentialClientApplication, SerializableTokenCache
import config
import os
import sys
import tempfile
from pathlib import Path


def write_atomic(path, text):
    """Replace path's contents in one step.

    Opening for write truncates before any bytes land, so a process killed
    mid-write leaves an empty file that still passes an existence check. The
    next run would then read a blank refresh token and need interactive
    re-authentication.
    """
    path = str(path)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


# Set to False if you only want to refresh the token files without printing
# the access token (e.g. for periodic refresh jobs).
print_access_token = True

cache = SerializableTokenCache()

app = ConfidentialClientApplication(
    client_id=config.ClientId,
    client_credential=config.ClientSecret or None,
    token_cache=cache,
    authority=config.Authority,
    timeout=getattr(config, "Timeout", 30),
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
write_atomic(refresh_path, new_refresh_token)

write_atomic(config.AccessTokenFileName, token["access_token"])

if print_access_token:
    # Printing the access token allows SMTP clients like msmtp to use this
    # script as password source (passwordeval).
    print(token["access_token"])