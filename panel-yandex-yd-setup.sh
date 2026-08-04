#!/bin/bash
set -euo pipefail

PROFILE="00000000-0000-0000-0000-000000000000"
BEHE_NODE="72c2928d-39e7-474e-959c-9e8762b196be"
YANDEX_HOST="14216581-e04e-4094-ac4e-d2597feb793e"
HE_TAG="Bee-CDN-XHTTP-HE"
YD_TAG="Bee-CDN-XHTTP-YD"
YD_PORT=7444
PATH_PREVIEW="/session/preview"
ENV_FILE="/opt/satkavpn/candelix.env"
PANEL="https://panel.satkaconnect.xyz"

TOKEN="$(grep ^REMNAWAVE_API_TOKEN= "$ENV_FILE" | cut -d= -f2-)"

api() {
  local method="$1"
  local path="$2"
  local body="${3:-}"
  if [ -n "$body" ]; then
    curl -sk -X "$method" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "$body" \
      "$PANEL$path"
  else
    curl -sk -X "$method" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      "$PANEL$path"
  fi
}

echo "[1] fetch profile"
api GET "/api/config-profiles/$PROFILE" > /tmp/profile_wrap.json

python3 << 'PY'
import json, copy

with open("/tmp/profile_wrap.json") as f:
    wrap = json.load(f)
profile = wrap["response"]
config = profile["config"]
he = next(ib for ib in config["inbounds"] if ib.get("tag") == "Bee-CDN-XHTTP-HE")
yd = copy.deepcopy(he)
yd["tag"] = "Bee-CDN-XHTTP-YD"
yd["port"] = 7444
yd["listen"] = "127.0.0.1"
xh = yd.setdefault("streamSettings", {}).setdefault("xhttpSettings", {})
xh["mode"] = "stream-one"
xh["path"] = "/session/preview"
extra = xh.get("extra")
if isinstance(extra, dict):
    extra["mode"] = "stream-one"
    extra["path"] = "/session/preview"
    for k in ("uplinkHTTPMethod", "uplinkDataPlacement", "uplinkDataKey"):
        extra.pop(k, None)

replaced = False
for i, ib in enumerate(config["inbounds"]):
    if ib.get("tag") == "Bee-CDN-XHTTP-YD":
        config["inbounds"][i] = yd
        replaced = True
        break
if not replaced:
    config["inbounds"].append(yd)

patch = {"uuid": profile["uuid"], "name": profile["name"], "config": config}
with open("/tmp/profile_patch.json", "w") as f:
    json.dump(patch, f)
print("inbounds:", len(config["inbounds"]), "YD port", yd["port"], "mode", xh["mode"])
PY

echo "[2] patch profile"
api PATCH "/api/config-profiles" "$(cat /tmp/profile_patch.json)" > /tmp/patch_resp.json
python3 -c "import json; d=json.load(open('/tmp/patch_resp.json')); print('patch ok', d.get('response',{}).get('uuid','?'))"

echo "[3] resolve inbound uuids"
api GET "/api/config-profiles/$PROFILE/inbounds" > /tmp/inbounds_wrap.json
python3 << 'PY'
import json
wrap = json.load(open("/tmp/inbounds_wrap.json"))
ibs = wrap["response"]["inbounds"]
he = next(ib for ib in ibs if ib["tag"] == "Bee-CDN-XHTTP-HE")
yd = next(ib for ib in ibs if ib["tag"] == "Bee-CDN-XHTTP-YD")
with open("/tmp/inbound_uuids.env", "w") as f:
    f.write(f"HE_UUID={he['uuid']}\n")
    f.write(f"YD_UUID={yd['uuid']}\n")
print("HE", he["uuid"], "YD", yd["uuid"])
PY
source /tmp/inbound_uuids.env

echo "[4] activate HE+YD on Be-He node"
NODE_PATCH=$(python3 -c "import json; print(json.dumps({'uuid':'$BEHE_NODE','configProfile':{'activeConfigProfileUuid':'$PROFILE','activeInbounds':['$HE_UUID','$YD_UUID']}}))")
api PATCH "/api/nodes" "$NODE_PATCH" > /tmp/node_patch.json
python3 -c "import json; print('node patch', json.load(open('/tmp/node_patch.json')).get('response',{}).get('name','?'))"

echo "[5] patch Yandex host"
HOST_PATCH=$(python3 << PY
import json
print(json.dumps({
  "uuid": "$YANDEX_HOST",
  "remark": "Yandex БС CDN",
  "address": "cdn.satkaconnect.xyz",
  "port": 443,
  "path": "$PATH_PREVIEW",
  "sni": "cdn.satkaconnect.xyz",
  "host": "cdn.satkaconnect.xyz",
  "alpn": "h2",
  "fingerprint": "firefox",
  "securityLayer": "TLS",
  "overrideSniFromAddress": False,
  "keepSniBlank": False,
  "inbound": {
    "configProfileUuid": "$PROFILE",
    "configProfileInboundUuid": "$YD_UUID"
  },
  "nodes": ["$BEHE_NODE"]
}))
PY
)
api PATCH "/api/hosts" "$HOST_PATCH" > /tmp/host_patch.json
python3 -c "import json; print('host patch', json.load(open('/tmp/host_patch.json')).get('response',{}).get('remark','?'))"

echo "[6] whitelist squad inbound"
docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c \
  "INSERT INTO internal_squad_inbounds (internal_squad_uuid, inbound_uuid)
   SELECT s.uuid, '$YD_UUID'::uuid FROM internal_squads s WHERE s.name ILIKE '%whitelist%'
   ON CONFLICT DO NOTHING;"

echo "[7] verify db"
docker exec remnawave-db psql -U postgres -d postgres -c \
  "SELECT h.remark, cpi.tag, cpi.port FROM hosts h JOIN config_profile_inbounds cpi ON h.config_profile_inbound_uuid=cpi.uuid WHERE h.remark ILIKE '%CDN%';"

echo "DONE"
