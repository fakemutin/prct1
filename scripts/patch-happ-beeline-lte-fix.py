#!/usr/bin/env python3
"""Fix Beeline LTE: keep native xhttp config, encode extra in vless URI."""
from pathlib import Path

path = Path("/opt/satkavpn/happ_merge.py")
text = path.read_text()

old_prepare = '''def prepare_beeline_whitelist_cfg(native_cfg: dict) -> dict:
    cfg = copy.deepcopy(native_cfg)
    cfg["remarks"] = BEELINE_WHITELIST_REMARK
    finalize_whitelist_cfg(cfg, ping_seed=BEELINE_WHITELIST_REMARK)
    return cfg'''

new_prepare = '''def prepare_beeline_whitelist_cfg(native_cfg: dict) -> dict:
    """Beeline CDN tunnel: keep Remnawave-native outbound (xhttp extra), no whitelist routing/DNS."""
    cfg = copy.deepcopy(native_cfg)
    cfg["remarks"] = BEELINE_WHITELIST_REMARK
    cfg.pop("dns", None)
    cfg.pop("routing", None)
    cfg.pop("burstObservatory", None)
    cfg.pop("observatory", None)
    apply_fake_ping_meta(cfg, BEELINE_WHITELIST_REMARK)
    return cfg'''

if old_prepare not in text:
    raise SystemExit("prepare_beeline_whitelist_cfg block not found")
text = text.replace(old_prepare, new_prepare)

# vless_outbound_to_uri: encode xhttp extra
needle = '''    elif net == "xhttp":
        xhttp = ss.get("xhttpSettings") or {}
        if xhttp.get("path"):
            params.append(f"path={quote(xhttp['path'], safe='')}")
        if xhttp.get("host"):
            params.append(f"host={quote(xhttp['host'], safe='')}")
        if xhttp.get("mode"):
            params.append(f"mode={quote(xhttp['mode'], safe='')}")'''

replacement = '''    elif net == "xhttp":
        xhttp = ss.get("xhttpSettings") or {}
        if xhttp.get("path"):
            params.append(f"path={quote(xhttp['path'], safe='')}")
        if xhttp.get("host"):
            params.append(f"host={quote(xhttp['host'], safe='')}")
        if xhttp.get("mode"):
            params.append(f"mode={quote(xhttp['mode'], safe='')}")
        extra = xhttp.get("extra")
        if extra:
            params.append(
                f"extra={quote(json.dumps(extra, separators=(',', ':')), safe='')}"
            )'''

if needle not in text:
    raise SystemExit("xhttp uri block not found")
text = text.replace(needle, replacement)

path.write_text(text)
print("patched OK")
