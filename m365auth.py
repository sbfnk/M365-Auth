"""
M365 OAuth2 authentication library
Shared code for getting and refreshing tokens
"""
import sys
import os
import argparse
import threading
import urllib.parse
import webbrowser
import ssl
import http.server
from pathlib import Path
from platformdirs import user_config_dir, user_cache_dir
import keyring
from msal import ConfidentialClientApplication, SerializableTokenCache


# Default configuration (used if no user config exists)
DEFAULT_CONFIG = {
    'ClientId': '9e5f94bc-e8a4-4e73-b8be-63364c29d753',  # Thunderbird's client ID
    'ClientSecret': '',
    'Authority': None,
    'Profiles': {
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
}


def load_config(profile='mail'):
    """Load config from XDG config dir, creating default if needed"""
    config_dir = Path(user_config_dir("m365auth"))
    config_file = config_dir / "config.py"

    if not config_file.exists():
        # Create config directory and write default config
        config_dir.mkdir(parents=True, exist_ok=True)
        config_content = """# M365 OAuth2 Configuration
# Thunderbird's public client ID (works for personal Microsoft accounts)
ClientId = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

# Client secret (can be empty for public clients like mail clients)
ClientSecret = ""

# Authority URL (None = multi-tenant, or specify tenant-specific URL)
Authority = None

# Profiles with different scope sets
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

# Default scopes (for backwards compatibility)
Scopes = Profiles['mail']['scopes']
"""
        config_file.write_text(config_content)
        print(f"Created default config at {config_file}")
        print("You can edit this file to customize settings.\n")

    # Load user config
    import importlib.util
    spec = importlib.util.spec_from_file_location("config", config_file)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)

    # Get scopes for the selected profile
    if hasattr(config, 'Profiles') and profile in config.Profiles:
        scopes = config.Profiles[profile]['scopes']
    elif hasattr(config, 'Scopes'):
        scopes = config.Scopes
    else:
        raise ValueError(f"No scopes found in config for profile '{profile}'")

    return config, scopes


def get_refresh_token(profile='mail'):
    """Get refresh token from keychain or file"""
    keychain_service = f"m365auth-{profile}"

    # Try keychain first
    refresh_token = None
    try:
        refresh_token = keyring.get_password(keychain_service, "refresh_token")
    except Exception:
        pass

    if not refresh_token:
        # Try file fallback
        cache_dir = Path(user_cache_dir("m365auth"))
        token_file = cache_dir / f"refresh_token_{profile}"
        if token_file.exists():
            refresh_token = token_file.read_text().strip()

    if not refresh_token:
        raise ValueError(
            f"No refresh token found in keychain or file for profile '{profile}'. "
            f"Run 'get-token --profile {profile}' first."
        )

    return refresh_token


def save_refresh_token(refresh_token, profile='mail'):
    """Save refresh token to keychain or file"""
    keychain_service = f"m365auth-{profile}"

    # Try keychain first, fall back to file if it fails
    try:
        keyring.set_password(keychain_service, "refresh_token", refresh_token)
    except Exception:
        # Fall back to file storage
        cache_dir = Path(user_cache_dir("m365auth"))
        cache_dir.mkdir(parents=True, exist_ok=True)
        token_file = cache_dir / f"refresh_token_{profile}"
        token_file.write_text(refresh_token)
        token_file.chmod(0o600)


def get_access_token(profile='mail'):
    """
    Get a fresh access token for the given profile.
    Returns the access token string.
    """
    config, scopes = load_config(profile)
    old_refresh_token = get_refresh_token(profile)

    # Get new access token using MSAL
    cache = SerializableTokenCache()
    app = ConfidentialClientApplication(
        config.ClientId,
        client_credential=config.ClientSecret,
        token_cache=cache,
        authority=config.Authority
    )

    token = app.acquire_token_by_refresh_token(old_refresh_token, scopes)

    if 'error' in token:
        raise ValueError(f"Failed to get access token: {token}")

    # Update refresh token (tokens rotate on each use)
    save_refresh_token(token['refresh_token'], profile)

    return token['access_token']

def generate_self_signed_cert(cert_file, key_file):
    """Generate a self-signed certificate for localhost"""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    import datetime
    import ipaddress

    # Generate private key
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Create certificate
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])

    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.UTC)
    ).not_valid_after(
        datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3650)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.IPAddress(ipaddress.IPv4Address(u"127.0.0.1")),
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())

    # Write private key
    with open(key_file, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Write certificate
    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))


# CLI Entry Points

def main_get_token():
    """Entry point for get-token command"""
    parser = argparse.ArgumentParser(description='Get OAuth2 token for M365 services')
    parser.add_argument('--server', action='store_true',
                        help='Force server mode even over SSH (for use with SSH tunnel)')
    parser.add_argument('--profile', type=str, default='mail',
                        help='Profile to use for scopes (default: mail). Available: mail, calendar')
    args = parser.parse_args()

    # Load config and get scopes
    config, scopes = load_config(args.profile)
    print(f"Using profile: {args.profile}")

    # Set up cache directory for SSL certs
    cache_dir = Path(user_cache_dir("m365auth"))
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Use profile name in keychain service name to keep tokens separate
    keychain_service = f"m365auth-{args.profile}"

    redirect_uri = "https://localhost:7598/"

    # We use the cache to extract the refresh token
    cache = SerializableTokenCache()
    app = ConfidentialClientApplication(config.ClientId, client_credential=config.ClientSecret, 
                                        token_cache=cache, authority=config.Authority)

    url = app.get_authorization_request_url(scopes, redirect_uri=redirect_uri)

    # webbrowser.open may fail silently
    print("Navigate to the following url in a web browser, if doesn't open automatically:")
    print(url)
    try:
        webbrowser.open(url)
    except Exception:
        pass

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed_url = urllib.parse.urlparse(self.path)
            parsed_query = urllib.parse.parse_qs(parsed_url.query)
            global code
            code = next(iter(parsed_query['code']), '')

            response_body = b'Success. Look back at your terminal.\r\n'
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', len(response_body))
            self.end_headers()
            self.wfile.write(response_body)

            global httpd
            t = threading.Thread(target=lambda: httpd.shutdown())
            t.start()

    code = ''

    server_address = ('', 7598)
    httpd = http.server.HTTPServer(server_address, Handler)

    # Use self-signed certs from cache dir, generate if missing
    keyf, certf = cache_dir / "server.key", cache_dir / "server.cert"
    if not (keyf.exists() and certf.exists()):
        print("Generating self-signed certificate for localhost...")
        generate_self_signed_cert(certf, keyf)

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certf, keyf)
    httpd.socket = context.wrap_socket(
        httpd.socket,
        server_side=True,
    )

    # If we are running over ssh then the browser on the local machine
    # would never be able access localhost:7598 (unless using SSH tunnel with --server flag)
    if not os.getenv('SSH_CONNECTION') or args.server:
        httpd.serve_forever()

    if code == '':
        print('After login, you will be redirected to a blank (or error) page with a url containing an access code. Paste the url below.')
        print('Response url: ', end='', flush=True)
        resp = sys.stdin.readline().strip()

        # Parse the code from the URL
        parsed = urllib.parse.urlparse(resp)
        query_params = urllib.parse.parse_qs(parsed.query)
        if 'code' in query_params:
            code = query_params['code'][0]
        else:
            # Fallback to simple string parsing
            i = resp.find('code=')
            if i >= 0:
                i += 5
                end = resp.find('&', i)
                code = resp[i:end] if end > 0 else resp[i:]
            else:
                code = resp

    token = app.acquire_token_by_authorization_code(code, scopes, redirect_uri=redirect_uri)

    if 'error' in token:
        print(token)
        sys.exit("Failed to get access token")

    # Store refresh token in system keychain (with file fallback for headless)
    try:
        keyring.set_password(keychain_service, "refresh_token", token['refresh_token'])
        print(f'Refresh token acquired and stored in system keychain ({keychain_service})')
    except Exception as e:
        print(f'⚠️  Could not store in keychain ({e}), falling back to file storage')
        token_file = cache_dir / f"refresh_token_{args.profile}"
        token_file.write_text(token['refresh_token'])
        token_file.chmod(0o600)  # Read/write for owner only
        print(f'Refresh token stored in {token_file} (mode 600)')

    # Print access token (don't persist to disk for security)
    print(f'\nAccess token (valid for ~1 hour):\n{token["access_token"]}')


def main_refresh_token():
    """Entry point for refresh-token command"""
    parser = argparse.ArgumentParser(description='Refresh OAuth2 token for M365 services')
    parser.add_argument('--profile', type=str, default='mail',
                        help='Profile to use for scopes (default: mail). Available: mail, calendar')
    args = parser.parse_args()

    try:
        access_token = get_access_token(args.profile)
        print(access_token)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main_get_refresh_token():
    """Entry point for get-refresh-token command"""
    parser = argparse.ArgumentParser(description='Get refresh token from keychain')
    parser.add_argument('--profile', type=str, default='mail',
                        help='Profile to use (default: mail). Available: mail, calendar')
    args = parser.parse_args()

    try:
        refresh_token = get_refresh_token(args.profile)
        print(refresh_token)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
