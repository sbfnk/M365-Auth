#!/usr/bin/env python3
"""Diagnostic tool to decode and inspect access tokens"""
import sys
import json
import base64

def decode_jwt(token):
    """Decode a JWT without verification to inspect claims"""
    try:
        # Split the JWT into header, payload, signature
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # Decode the payload (add padding if needed)
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        print(f"Error decoding JWT: {e}", file=sys.stderr)
        return None

def main():
    # Import here so we can catch import errors
    try:
        from msal import PublicClientApplication, SerializableTokenCache
        import keyring
        from pathlib import Path
        from platformdirs import user_config_dir

        # Load config
        sys.path.insert(0, str(Path.home() / ".config" / "m365auth"))
        try:
            import config
        except ImportError:
            sys.path.insert(0, str(Path(__file__).parent))
            import config

        # Get token
        print("Fetching access token...")
        keychain_service = "m365-imap-mail"
        old_refresh_token = keyring.get_password(keychain_service, "default")

        if not old_refresh_token:
            print("ERROR: No refresh token found in keychain", file=sys.stderr)
            sys.exit(1)

        # Try to get fresh access token
        cache = SerializableTokenCache()
        if not config.ClientSecret or config.ClientSecret == "":
            app = PublicClientApplication(config.ClientId, token_cache=cache, authority=config.Authority)
        else:
            from msal import ConfidentialClientApplication
            app = ConfidentialClientApplication(
                config.ClientId,
                client_credential=config.ClientSecret,
                token_cache=cache,
                authority=config.Authority
            )

        scopes = config.Profiles.get('mail', {}).get('scopes', config.Scopes)
        result = app.acquire_token_by_refresh_token(old_refresh_token, scopes)

        if "access_token" not in result:
            print("ERROR: Failed to get access token", file=sys.stderr)
            print(f"Error: {result.get('error')}", file=sys.stderr)
            print(f"Description: {result.get('error_description')}", file=sys.stderr)
            sys.exit(1)

        access_token = result["access_token"]
        print(f"\nAccess token obtained (length: {len(access_token)})")

        # Decode and inspect the JWT
        claims = decode_jwt(access_token)
        if claims:
            print("\n=== Token Claims ===")
            print(f"Audience (aud): {claims.get('aud')}")
            print(f"Issuer (iss): {claims.get('iss')}")
            print(f"Subject (sub): {claims.get('sub')}")
            print(f"UPN: {claims.get('upn')}")
            print(f"Email: {claims.get('email')}")
            print(f"App ID (appid): {claims.get('appid')}")

            # Check scopes
            scp = claims.get('scp', '')
            print(f"\nGranted scopes: {scp}")

            # Check if IMAP scope is present
            if 'IMAP.AccessAsUser.All' in scp:
                print("✓ IMAP.AccessAsUser.All scope is present")
            else:
                print("✗ IMAP.AccessAsUser.All scope is MISSING!")

            if 'SMTP.Send' in scp:
                print("✓ SMTP.Send scope is present")
            else:
                print("✗ SMTP.Send scope is MISSING!")

            # Check audience
            expected_aud = "https://outlook.office365.com"
            if claims.get('aud') in [expected_aud, "https://outlook.office.com", "00000002-0000-0ff1-ce00-000000000000"]:
                print(f"✓ Audience is correct for Exchange")
            else:
                print(f"✗ Audience might be wrong: {claims.get('aud')}")

            # Check expiry
            import time
            exp = claims.get('exp', 0)
            if exp:
                exp_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))
                if exp > time.time():
                    print(f"✓ Token is valid until {exp_time}")
                else:
                    print(f"✗ Token expired at {exp_time}")

        print("\n=== XOAUTH2 String (for testing) ===")
        user = claims.get('upn') or claims.get('email') or 'user'
        auth_string = f"user={user}\x01auth=Bearer {access_token}\x01\x01"
        encoded = base64.b64encode(auth_string.encode()).decode()
        print(f"Length: {len(encoded)}")
        print(f"First 100 chars: {encoded[:100]}...")

    except ImportError as e:
        print(f"ERROR: Missing dependency: {e}", file=sys.stderr)
        print("Run: pip install m365auth", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
