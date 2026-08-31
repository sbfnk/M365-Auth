#!/bin/bash
# Simple diagnostic script to check authentication setup

echo "=== M365-Auth Diagnostic ==="
echo ""

# Check refresh token
echo "1. Checking keychain for refresh token..."
if security find-generic-password -s "m365auth-mail" -w > /dev/null 2>&1; then
    echo "   ✓ Refresh token found in keychain"
    token=$(security find-generic-password -s "m365auth-mail" -w 2>/dev/null)
    echo "   Token starts with: ${token:0:50}..."
else
    echo "   ✗ No refresh token found"
    echo "   Run: get-token --profile mail"
    exit 1
fi

# Check config
echo ""
echo "2. Checking configuration..."
if [ -f ~/.config/m365auth/config.py ]; then
    echo "   ✓ Custom config found: ~/.config/m365auth/config.py"
    client_id=$(grep "^ClientId" ~/.config/m365auth/config.py | cut -d'"' -f2)
    authority=$(grep "^Authority" ~/.config/m365auth/config.py | grep -v "^#" | cut -d'"' -f2)
else
    echo "   Using default config.py"
    client_id=$(grep "^ClientId" config.py | cut -d'"' -f2)
    authority=$(grep "^Authority" config.py | grep -v "^#" | cut -d'=' -f2 | tr -d ' ')
fi

echo "   Client ID: $client_id"
echo "   Authority: ${authority:-None (multi-tenant)}"

# Check if using Thunderbird's public client
if [ "$client_id" = "9e5f94bc-e8a4-4e73-b8be-63364c29d753" ]; then
    echo ""
    echo "⚠️  WARNING: You're using Thunderbird's public client ID"
    echo "   This may not work with organizational accounts (@lshtm.ac.uk)"
    echo ""
    echo "   SOLUTION: Create your own Azure app registration"
    echo "   See README.md section: 'Azure App Registration Setup'"
fi

# Check authority for organizational account
if [ "$authority" = "None" ] || [ -z "$authority" ]; then
    echo ""
    echo "⚠️  WARNING: Using multi-tenant authority (/common)"
    echo "   For organizational accounts, you should use tenant-specific authority"
    echo ""
    echo "   SOLUTION:"
    echo "   1. Find your tenant ID at: https://entra.microsoft.com"
    echo "   2. Create ~/.config/m365auth/config.py with:"
    echo "      Authority = \"https://login.microsoftonline.com/YOUR-TENANT-ID/\""
fi

echo ""
echo "=== Common Issues & Solutions ==="
echo ""
echo "If authentication is failing, try these steps:"
echo ""
echo "1. Re-authenticate (refresh token may be invalid):"
echo "   $ get-token --profile mail"
echo ""
echo "2. For organizational accounts (@lshtm.ac.uk), create your own Azure app:"
echo "   a. Go to https://entra.microsoft.com"
echo "   b. Create new app registration (see README.md for details)"
echo "   c. Add permissions: IMAP.AccessAsUser.All, SMTP.Send"
echo "   d. Grant admin consent"
echo "   e. Create ~/.config/m365auth/config.py with your ClientId and Authority"
echo ""
echo "3. Check with your IT department:"
echo "   - Are third-party OAuth apps allowed?"
echo "   - Is IMAP/SMTP access enabled for your account?"
echo "   - Are there Conditional Access policies blocking authentication?"
echo ""
