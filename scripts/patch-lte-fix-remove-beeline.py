#!/usr/bin/env python3
"""Remove Beeline from subscriptions + fix LTE on regular locations."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

# Beeline off by default
text = text.replace(
    '"BEELINE_IN_SUBSCRIPTION", "true"',
    '"BEELINE_IN_SUBSCRIPTION", "false"',
)
text = text.replace(
    '"BEELINE_IN_SUBSCRIPTION", "true"\n).lower()',
    '"BEELINE_IN_SUBSCRIPTION", "false"\n).lower()',
)

# keyword in routing breaks LTE
if "if not d.startswith(\"regexp:\")" in text:
    text = text.replace(
        "        [d for d in REGULAR_ADBLOCK_DOMAINS if not d.startswith(\"regexp:\")]",
        "        [d for d in REGULAR_ADBLOCK_DOMAINS if d.startswith((\"domain:\", \"full:\"))]",
        1,
    )
    print("routing adblock: domain/full only")

# Remove ensure_beeline from mom merge
text = text.replace(
    "    ensure_beeline_whitelist_entry(result, natives, satka=satka)\n\n    stable,",
    "\n    stable,",
    1,
)

path.write_text(text)
print("happ_merge LTE/beeline patch OK")

# Docker env: disable Beeline in subscription
import subprocess

for envfile in ("/opt/satkavpn/candelix.env", "/opt/satkavpn/.env"):
    p = Path(envfile)
    if not p.exists():
        continue
    body = p.read_text()
    if "BEELINE_IN_SUBSCRIPTION=false" in body:
        print(f"{envfile}: already false")
    elif "BEELINE_IN_SUBSCRIPTION" in body:
        body = __import__("re").sub(
            r"BEELINE_IN_SUBSCRIPTION=.*",
            "BEELINE_IN_SUBSCRIPTION=false",
            body,
        )
        p.write_text(body)
        print(f"{envfile}: set false")
    else:
        p.write_text(body.rstrip() + "\nBEELINE_IN_SUBSCRIPTION=false\n")
        print(f"{envfile}: added false")

subprocess.run(["docker", "restart", "happ-merge"], check=False)
print("happ-merge restarted")
