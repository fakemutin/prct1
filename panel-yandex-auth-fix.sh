#!/bin/bash
set -euo pipefail

# Yandex CDN: auth for all paid users (free squad) + packet-up GET on YD inbound

PROFILE="00000000-0000-0000-0000-000000000000"
BEHE_NODE="72c2928d-39e7-474e-959c-9e8762b196be"
YANDEX_HOST="14216581-e04e-4094-ac4e-d2597feb793e"
FREE_SQUAD="b4d1b0f0-62bb-496a-b1d1-2618a7374313"
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

echo "[1] free squad: YD inbound auth + hide Yandex host from free native sub"
docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c \
  "INSERT INTO internal_squad_inbounds (internal_squad_uuid, inbound_uuid) VALUES ('$FREE_SQUAD', '$YD inbound placeholder');" 2>/dev/null || true
docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c \
  "INSERT INTO internal_squad_inbounds (internal_squad_uuid, inbound_uuid) SELECT '$FREE_SQUAD'::uuid, uuid FROM config_profile_inbounds WHERE tag = '$YD_TAG' ON CONFLICT DO NOTHING;"
docker exec remnawave-db psql -U postgres -d postgres -v ON_ERROR_STOP=1 -c \
  "INSERT INTO internal_squad_host_exclusions (host_uuid, squad_uuid) VALUES ('$YANDEX_HOST', '$FREE_SQUAD') ON CONFLICT DO NOTHING;"

echo "[2] YD inbound -> packet-up (GET uplink, no POST on edge)"
api GET "/api/config-profiles/$PROFILE" > /tmp/profile_wrap.json

python3 << 'PY'
import json, copy

with open("/tmp/profile_wrap.json") as f:
    profile = json.load(f)["response"]
config = profile["config"]
he = next(ib for ib in config["inbounds"] if ib.get("tag") == "Bee-CDN-XHTTP-HE")
yd = next((ib for ib in config["inbounds"] if ib.get("tag") == "Bee-CDN-XHTTP-YD"), None)
if yd is None:
    yd = copy.deepcopy(he)
    config["inbounds"].append(yd)
yd["tag"] = "Bee-CDN-XHTTP-YD"
yd["port"] = 7444
yd["listen"] = "127.0.0.1"
xh = yd.setdefault("streamSettings", {}).setdefault("xhttpSettings", {})
xh["mode"] = "packet-up"
xh["path"] = "/session/preview"
extra = xh.get("extra")
if isinstance(extra, dict):
    extra["mode"] = "packet-up"
    extra["path"] = "/session/preview"
    extra.pop("uplinkHTTPMethod", None)
    extra.pop("uplinkDataPlacement", None)
    extra.pop("uplinkDataKey", None)
for i, ib in enumerate(config["inbounds"]):
    if ib.get("tag") == "Bee-CDN-XHTTP-YD":
        config["inbounds"][i] = yd
        break

patch = {"uuid": profile["uuid"], "name": profile["name"], "config": config}
with open("/tmp/profile_patch.json", "w") as f:
    json.dump(patch, f)
print("YD mode", xh["mode"], "port", yd["port"])
PY

api PATCH "/api/config-profiles" "$(cat /tmp/profile_patch.json)" > /tmp/patch_resp.json

echo "[3] node active inbounds"
api GET "/api/config-profiles/$PROFILE/inbounds" > /tmp/inbounds_wrap.json
python3 << 'PY'
import json
ibs = json.load(open("/tmp/inbounds_wrap.json"))["response"]["inbounds"]
he = next(ib for ib in ibs if ib["tag"] == "Bee-CDN-XHTTP-HE")
yd = next(ib for ib in ibs if ib["tag"] == "Bee-CDN-XHTTP-YD")
open("/tmp/inbound_uuids.env", "w").write(f"HE_UUID={he['uuid']}\nYD_UUID={yd['uuid']}\n")
print("HE", he["uuid"], "YD", yd["uuid"])
PY
source /tmp/inbound_uuids.env

NODE_PATCH=$(python3 -c "import json; print(json.dumps({'uuid':'$BEHE_NODE','configProfile':{'activeConfigProfileUuid':'$PROFILE','activeInbounds':['$HE_UUID','$YD_UUID']}}))")
api PATCH "/api/nodes" "$NODE_PATCH" > /dev/null

echo "[4] restart Be-He remnanode via API"
api POST "/api/nodes/$BEHE_NODE/actions/restart" > /tmp/restart.json 2>/dev/null || true

docker exec remnawave-db psql -U postgres -d postgres -c \
  "SELECT s.name, cpi.tag FROM internal_squads s JOIN internal_squad_inbounds isi ON isi.internal_squad_uuid=s.uuid JOIN config_profile_inbounds cpi ON cpi.uuid=isi.inbound_uuid WHERE cpi.tag LIKE 'Bee-CDN%' ORDER BY s.name, cpi.tag;"

echo "DONE"
