#!/usr/bin/env python3
import json
import subprocess

PROFILE = "00000000-0000-0000-0000-000000000000"
TAG = "Bee-CDN-XHTTP-HE"

raw = subprocess.check_output(
    [
        "docker",
        "exec",
        "remnawave-db",
        "psql",
        "-U",
        "postgres",
        "-d",
        "postgres",
        "-t",
        "-A",
        "-c",
        f"SELECT config::text FROM config_profiles WHERE uuid='{PROFILE}';",
    ],
    text=True,
)
cfg = json.loads(raw)
for ib in cfg["inbounds"]:
    if ib.get("tag") != TAG:
        continue
    xh = ib["streamSettings"]["xhttpSettings"]
    extra = xh.setdefault("extra", {})
    extra["uplinkDataPlacement"] = "auto"
    extra.setdefault("uplinkHTTPMethod", "POST")
    xh["mode"] = "packet-up"
    extra.setdefault("mode", "packet-up")
    print("patched", extra.get("uplinkDataPlacement"))
    break

payload = json.dumps(cfg, ensure_ascii=False).replace("'", "''")
sql = (
    f"UPDATE config_profiles SET config = '{payload}'::jsonb "
    f"WHERE uuid='{PROFILE}';"
)
subprocess.run(
    [
        "docker",
        "exec",
        "remnawave-db",
        "psql",
        "-U",
        "postgres",
        "-d",
        "postgres",
        "-c",
        sql,
    ],
    check=True,
)
print("ok")
