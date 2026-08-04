#!/usr/bin/env python3
"""Add TLS client settings for Beeline CDN (port 443 requires TLS + trbcdn SNI)."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

# See scripts/patch-happ-beeline-lte-fix.py and patch-happ-beeline-uuid.py for prior patches.
# This file documents the TLS fix applied in apply_beeline_client_tls().

if "def apply_beeline_client_tls" not in text:
    raise SystemExit("apply_beeline_client_tls missing - run full patch chain first")
print("TLS helper already present")
