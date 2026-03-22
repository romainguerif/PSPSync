#!/usr/bin/env python3
"""
PSP Sync — Sync save data between a real PSP and PPSSPP.
"""

import os
import json
import shutil
import time
import threading
import platform
import string
from datetime import datetime

import webview

# ─── Platform ────────────────────────────────────────────────────────────────

SYSTEM = platform.system()

def find_psp_volume():
    if SYSTEM == "Darwin":
        if os.path.isdir("/Volumes/PSP"):
            return "/Volumes/PSP"
    elif SYSTEM == "Linux":
        for base in ["/media", "/mnt"]:
            if not os.path.isdir(base):
                continue
            psp = os.path.join(base, "PSP")
            if os.path.isdir(os.path.join(psp, "PSP", "SAVEDATA")):
                return psp
            for sub in os.listdir(base):
                psp = os.path.join(base, sub, "PSP")
                if os.path.isdir(os.path.join(psp, "PSP", "SAVEDATA")):
                    return psp
    elif SYSTEM == "Windows":
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.isdir(os.path.join(drive, "PSP", "SAVEDATA")):
                return drive
    return None

# ─── Config ──────────────────────────────────────────────────────────────────

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(APP_DIR, "pspsync.json")
DEFAULT_PPSSPP = os.path.join(APP_DIR, "PPSSPP-PSP", "PSP", "SAVEDATA")

def load_config():
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

config = load_config()

# ─── Sync Logic ──────────────────────────────────────────────────────────────

def get_psp_savedata():
    custom = config.get("psp_volume", "")
    if custom:
        sd = os.path.join(custom, "PSP", "SAVEDATA")
        if os.path.isdir(sd):
            return sd
    vol = find_psp_volume()
    if vol:
        return os.path.join(vol, "PSP", "SAVEDATA")
    return None

def get_ppsspp_savedata():
    return config.get("ppsspp_savedata", DEFAULT_PPSSPP)

def count_saves(path):
    if not path or not os.path.isdir(path):
        return 0
    return len([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])

def sync_savedata(src, dst):
    os.makedirs(dst, exist_ok=True)
    copied, skipped, errors = [], [], []
    if not os.path.isdir(src):
        return copied, skipped, [f"Source not found: {src}"]
    for name in sorted(os.listdir(src)):
        src_f, dst_f = os.path.join(src, name), os.path.join(dst, name)
        if not os.path.isdir(src_f):
            continue
        try:
            sf = [f for f in os.listdir(src_f) if os.path.isfile(os.path.join(src_f, f))]
            src_mt = max((os.path.getmtime(os.path.join(src_f, f)) for f in sf), default=0)
            dst_mt = 0
            if os.path.isdir(dst_f):
                df = [f for f in os.listdir(dst_f) if os.path.isfile(os.path.join(dst_f, f))]
                dst_mt = max((os.path.getmtime(os.path.join(dst_f, f)) for f in df), default=0)
            if src_mt > dst_mt:
                if os.path.exists(dst_f):
                    shutil.rmtree(dst_f)
                shutil.copytree(src_f, dst_f)
                copied.append(name)
            else:
                skipped.append(name)
        except Exception as e:
            errors.append(f"{name}: {e}")
    return copied, skipped, errors

# ─── API for JS ──────────────────────────────────────────────────────────────

class Api:
    def __init__(self):
        self.window = None

    def get_status(self):
        psp = get_psp_savedata()
        ppsspp = get_ppsspp_savedata()
        return {
            "psp_connected": psp is not None,
            "psp_saves": count_saves(psp),
            "pc_saves": count_saves(ppsspp),
            "psp_path": config.get("psp_volume", "") or "Auto-detect",
            "ppsspp_path": ppsspp,
        }

    def pull(self):
        psp = get_psp_savedata()
        if not psp:
            return {"log": "PSP not detected!"}
        t0 = time.time()
        copied, skipped, errors = sync_savedata(psp, get_ppsspp_savedata())
        return self._result(copied, skipped, errors, time.time() - t0, "PSP → PC")

    def push(self):
        psp = get_psp_savedata()
        if not psp:
            return {"log": "PSP not detected!"}
        t0 = time.time()
        copied, skipped, errors = sync_savedata(get_ppsspp_savedata(), psp)
        return self._result(copied, skipped, errors, time.time() - t0, "PC → PSP")

    def _result(self, copied, skipped, errors, dt, label):
        lines = []
        if copied:
            lines.append(f"{label} — {len(copied)} save(s) copied ({dt:.1f}s)")
            for n in copied:
                lines.append(f"  → {n}")
        if skipped:
            lines.append(f"{len(skipped)} save(s) already up to date")
        if errors:
            for e in errors:
                lines.append(f"ERROR: {e}")
        if not copied and not errors:
            lines.append(f"{label} — All synced")
        return {"log": "\n".join(lines)}

    def pick_psp(self):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            d = result[0]
            if os.path.isdir(os.path.join(d, "PSP", "SAVEDATA")):
                config["psp_volume"] = d
                save_config(config)
                return {"path": d}
            else:
                return {"error": f"No PSP/SAVEDATA in {d}"}
        return {}

    def reset_psp(self):
        config["psp_volume"] = ""
        save_config(config)
        return {"path": "Auto-detect"}

    def pick_ppsspp(self):
        result = self.window.create_file_dialog(webview.FOLDER_DIALOG)
        if result and len(result) > 0:
            d = result[0]
            config["ppsspp_savedata"] = d
            save_config(config)
            return {"path": d}
        return {}

# ─── HTML ────────────────────────────────────────────────────────────────────

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, 'Segoe UI', sans-serif;
    background: #0A0A0A;
    color: #fff;
    padding: 20px 24px;
    user-select: none;
    -webkit-user-select: none;
  }

  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .title { font-size: 22px; font-weight: 700; }
  .status { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #777; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: #555; }
  .dot.on { background: #fff; }

  .sep { height: 1px; background: #222; margin: 12px 0; }

  .field { margin-bottom: 12px; }
  .field-label { font-size: 11px; color: #666; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
  .field-row { display: flex; gap: 6px; align-items: center; }
  .field-path {
    flex: 1; background: #151515; padding: 6px 10px; border-radius: 6px;
    font-family: 'Menlo', 'Consolas', monospace; font-size: 11px;
    color: #999; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    border: 1px solid #222;
  }
  .btn-sm {
    background: #1A1A1A; color: #ccc; border: 1px solid #333; padding: 6px 12px;
    border-radius: 6px; font-size: 11px; cursor: pointer; white-space: nowrap;
  }
  .btn-sm:hover { background: #252525; border-color: #444; }
  .btn-sm.accent { color: #fff; }

  .cards { display: flex; gap: 8px; margin: 12px 0; }
  .card {
    flex: 1; background: #151515; border-radius: 8px; padding: 10px 14px;
    border: 1px solid #222;
  }
  .card-label { font-size: 11px; color: #666; }
  .card-value { font-size: 22px; font-weight: 700; margin-top: 2px; }

  .actions { display: flex; flex-direction: column; gap: 8px; margin: 14px 0; }
  .btn {
    width: 100%; padding: 14px; border: none; border-radius: 10px;
    font-size: 15px; font-weight: 700; color: #000; cursor: pointer;
    transition: filter 0.15s;
  }
  .btn:hover { filter: brightness(0.9); }
  .btn:active { filter: brightness(0.8); }
  .btn.pull { background: #fff; }
  .btn.push { background: #333; color: #fff; }
  .btn:disabled { opacity: 0.3; cursor: default; filter: none; }

  .log {
    background: #111; border-radius: 8px; padding: 10px 12px;
    font-family: 'Menlo', 'Consolas', monospace; font-size: 10px;
    color: #888; line-height: 1.6; min-height: 80px; max-height: 140px;
    overflow-y: auto; border: 1px solid #222;
  }
</style>
</head>
<body>

<div class="header">
  <div class="title">PSP Sync</div>
  <div class="status">
    <span id="statusText">Disconnected</span>
    <div class="dot" id="statusDot"></div>
  </div>
</div>

<div class="sep"></div>

<div class="field">
  <div class="field-label">PSP Folder</div>
  <div class="field-row">
    <div class="field-path" id="pspPath">Auto-detect</div>
    <button class="btn-sm" onclick="pickPsp()">Browse</button>
    <button class="btn-sm accent" onclick="resetPsp()">Auto</button>
  </div>
</div>

<div class="field">
  <div class="field-label">PPSSPP Folder</div>
  <div class="field-row">
    <div class="field-path" id="ppssppPath">...</div>
    <button class="btn-sm" onclick="pickPpsspp()">Browse</button>
  </div>
</div>

<div class="sep"></div>

<div class="cards">
  <div class="card">
    <div class="card-label">PSP</div>
    <div class="card-value" id="pspCount">—</div>
  </div>
  <div class="card">
    <div class="card-label">PPSSPP</div>
    <div class="card-value" id="pcCount">—</div>
  </div>
</div>

<div class="actions">
  <button class="btn pull" id="btnPull" onclick="pull()" disabled>PSP → PC</button>
  <button class="btn push" id="btnPush" onclick="push()" disabled>PC → PSP</button>
</div>

<div class="log" id="log"></div>

<script>
function ts() {
  const d = new Date();
  return d.toTimeString().slice(0, 8);
}

function log(msg) {
  const el = document.getElementById('log');
  el.innerHTML += '[' + ts() + ']  ' + msg.replace(/\\n/g, '<br>') + '<br>';
  el.scrollTop = el.scrollHeight;
}

function shorten(p, n) {
  if (!p) return '—';
  return p.length <= n ? p : '...' + p.slice(-(n - 3));
}

async function refresh() {
  const s = await pywebview.api.get_status();
  document.getElementById('statusDot').className = 'dot' + (s.psp_connected ? ' on' : '');
  document.getElementById('statusText').textContent = s.psp_connected ? 'Connected' : 'Disconnected';
  document.getElementById('pspCount').textContent = s.psp_connected ? s.psp_saves + ' saves' : '—';
  document.getElementById('pcCount').textContent = s.pc_saves > 0 ? s.pc_saves + ' saves' : '—';
  document.getElementById('btnPull').disabled = !s.psp_connected;
  document.getElementById('btnPush').disabled = !s.psp_connected;
  document.getElementById('pspPath').textContent = shorten(s.psp_path, 36);
  document.getElementById('ppssppPath').textContent = shorten(s.ppsspp_path, 40);
}

async function pull() {
  document.getElementById('btnPull').disabled = true;
  document.getElementById('btnPush').disabled = true;
  log('Syncing PSP → PC...');
  const r = await pywebview.api.pull();
  log(r.log);
  refresh();
}

async function push() {
  document.getElementById('btnPull').disabled = true;
  document.getElementById('btnPush').disabled = true;
  log('Syncing PC → PSP...');
  const r = await pywebview.api.push();
  log(r.log);
  refresh();
}

async function pickPsp() {
  const r = await pywebview.api.pick_psp();
  if (r.error) log(r.error);
  else if (r.path) { log('PSP: ' + r.path); refresh(); }
}

async function resetPsp() {
  await pywebview.api.reset_psp();
  log('PSP: auto-detect');
  refresh();
}

async function pickPpsspp() {
  const r = await pywebview.api.pick_ppsspp();
  if (r.path) { log('PPSSPP: ' + r.path); refresh(); }
}

window.addEventListener('pywebviewready', () => {
  log('Ready');
  refresh();
  setInterval(refresh, 2000);
});
</script>

</body>
</html>
"""

# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    api = Api()
    window = webview.create_window(
        "PSP Sync", html=HTML, js_api=api,
        width=440, height=520, resizable=False,
        background_color="#0A0A0A"
    )
    api.window = window
    webview.start()
