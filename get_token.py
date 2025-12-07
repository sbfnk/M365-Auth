from msal import ConfidentialClientApplication, SerializableTokenCache
import config
import http.server
import os
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path
import ssl

# Redirect URI for the local helper. This must match the URI used when
# granting consent to the client in Azure AD (Thunderbird uses this).
redirect_uri = "https://localhost:7598/"

# Use a token cache so MSAL can manage tokens if needed.
cache = SerializableTokenCache()

app = ConfidentialClientApplication(
    client_id=config.ClientId,
    client_credential=config.ClientSecret or None,
    token_cache=cache,
    authority=config.Authority,
)

# Build the authorization URL for the browser-based login.
url = app.get_authorization_request_url(config.Scopes, redirect_uri=redirect_uri)

print("Navigate to the following URL in a web browser (it may open automatically):")
print(url)
try:
    webbrowser.open(url)
except Exception:
    # In headless / SSH environments this may fail; user can copy-paste the URL.
    pass


#Minimal HTTPS handler to capture the ?code=... from the redirect.
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        parsed_query = urllib.parse.parse_qs(parsed_url.query)
        global code
        code = next(iter(parsed_query.get("code", [""])), "")

        response_body = b"Success. You can return to the terminal.\r\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", len(response_body))
        self.end_headers()
        self.wfile.write(response_body)

        # Stop the HTTP server after this request.
        global httpd
        t = threading.Thread(target=httpd.shutdown)
        t.start()


code = ""

# Start a small HTTPS server on localhost to receive the redirect.
server_address = ("", 7598)
httpd = http.server.HTTPServer(server_address, Handler)
root = Path(__file__).parent
keyf, certf = root / "server.key", root / "server.cert"
assert keyf.exists() and certf.exists(), "server.key / server.cert not found"
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certf, keyf)
httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

# If we are running over SSH, the local browser cannot reach the remote
# localhost:7598; in that case we will fall back to manual pasting.
if not os.getenv("SSH_CONNECTION"):
    httpd.serve_forever()

# Fallback: if the local HTTPS server did not receive a code, ask the user
# to paste the final redirect URL manually.
if code == "":
    print(
        "After login, you will be redirected to a (possibly blank) page "
        "with a URL containing an access code."
    )
    resp = input("Paste that full URL here: ").strip()

    i = resp.find("code=") + 5
    code = resp[i : resp.find("&", i)] if i > 4 else resp

# Exchange the authorization code for tokens.
token = app.acquire_token_by_authorization_code(
    code, scopes=config.Scopes, redirect_uri=redirect_uri
)

if "error" in token:
    print(token)
    sys.exit("Failed to get access token")

with open(config.RefreshTokenFileName, "w") as f:
    print(f"Refresh token acquired, writing to file {config.RefreshTokenFileName}")
    f.write(token["refresh_token"])

with open(config.AccessTokenFileName, "w") as f:
    print(f"Access token acquired, writing to file {config.AccessTokenFileName}")
    f.write(token["access_token"])