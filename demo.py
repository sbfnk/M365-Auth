"""
Interactive demo for Microsoft 365 IMAP/SMTP using OAuth 2.0 authentication.

This script demonstrates reading inbox messages and sending emails via XOAUTH2.
Before running this, use `get_token.py` to obtain the initial refresh token.
This script automatically refreshes the access token on each run using the
stored refresh token, so no manual token management is needed.
"""
import base64
import imaplib
import smtplib
import sys
from email.message import EmailMessage

from msal import ConfidentialClientApplication, SerializableTokenCache

import config


IMAP_HOST = "outlook.office365.com"
SMTP_HOST = "smtp.office365.com"
SMTP_PORT = 587


# Create an MSAL client using the settings from config.py.
def _get_app():
    cache = SerializableTokenCache()
    return ConfidentialClientApplication(
        client_id=config.ClientId,
        client_credential=config.ClientSecret or None,
        token_cache=cache,
        authority=config.Authority,
    )


#Get a fresh access token using the stored refresh token.
def acquire_access_token() -> str:
    try:
        # Note how we consume the refresh token from the file written 
        # by get_token.py
        with open(config.RefreshTokenFileName, "r") as f:
            refresh_token = f.read().strip()
    except FileNotFoundError:
        sys.exit(
            f"Refresh token file {config.RefreshTokenFileName} not found. "
            "Run get_token.py first."
        )

    app = _get_app()
    token = app.acquire_token_by_refresh_token(refresh_token, scopes=config.Scopes)
    if "error" in token:
        print(token)
        sys.exit("Failed to get access token")

    # Optionally, update stored refresh token if a new one is returned.
    new_refresh_token = token.get("refresh_token", refresh_token)
    with open(config.RefreshTokenFileName, "w") as f:
        f.write(new_refresh_token)

    # Keep the latest access token around (optional).
    with open(config.AccessTokenFileName, "w") as f:
        f.write(token["access_token"])

    return token["access_token"]

# Build the raw XOAUTH2 auth string (not base64 encoded).
def build_raw_xoauth2(username: str, access_token: str) -> str:
    # imaplib.authenticate expects the callback to return this raw string.
    return f"user={username}\1auth=Bearer {access_token}\1\1"


# Print the most recent messages from the inbox.
def show_inbox(user_email: str, limit: int = 15) -> None:
    access_token = acquire_access_token()
    raw_auth = build_raw_xoauth2(user_email, access_token)

    print(f"Connecting to IMAP as {user_email}...")
    imap = imaplib.IMAP4_SSL(IMAP_HOST)
    try:
        # imaplib will base64-encode the returned string for us.
        imap.authenticate("XOAUTH2", lambda _: raw_auth)
        typ, _ = imap.select("INBOX")
        if typ != "OK":
            print("Failed to select INBOX")
            return

        typ, data = imap.search(None, "ALL")
        if typ != "OK" or not data or not data[0]:
            print("No messages found.")
            return

        all_ids = data[0].split()
        last_ids = all_ids[-limit:]
        print(f"Showing up to last {len(last_ids)} messages:\n")

        for msg_id in reversed(last_ids):
            typ, msg_data = imap.fetch(
                msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])"
            )
            if typ != "OK" or not msg_data:
                continue
            raw_header = msg_data[0][1].decode("utf-8", errors="replace")
            print("-" * 60)
            print(raw_header.strip())
    finally:
        try:
            imap.close()
        except Exception:
            pass
        imap.logout()

# Prompt for a simple message and send it via SMTP on behalf of the user.
def send_message(user_email: str) -> None:
    access_token = acquire_access_token()
    raw_auth = build_raw_xoauth2(user_email, access_token)

    to_line = input("To (comma-separated): ").strip()
    if not to_line:
        print("No recipients given.")
        return
    recipients = [addr.strip() for addr in to_line.split(",") if addr.strip()]

    subject = input("Subject: ").strip()
    print("Message body (single line):")
    body = input().strip()

    msg = EmailMessage()
    msg["From"] = user_email
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    print(f"Connecting to SMTP as {user_email}...")
    smtp = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
    try:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        # For SMTP the *base64-encoded* auth string must be sent manually.
        xoauth2_b64 = base64.b64encode(raw_auth.encode("utf-8")).decode("ascii")
        code, resp = smtp.docmd("AUTH", "XOAUTH2 " + xoauth2_b64)
        if code != 235:
            print("SMTP AUTH failed:", code, resp)
            return

        smtp.send_message(msg)
        print("Message sent.")
    finally:
        smtp.quit()


def main():
    print("Simple M365 demo using the tokens from get_token.py / refresh_token.py")
    user_email = input("Your M365 email address: ").strip()
    if not user_email:
        sys.exit("No email address provided.")

    choice = input("Type 'inbox' to list messages or 'message' to send: ").strip().lower()

    if choice == "inbox":
        show_inbox(user_email)
    elif choice == "message":
        send_message(user_email)
    else:
        print("Unknown choice, exiting.")


if __name__ == "__main__":
    main()