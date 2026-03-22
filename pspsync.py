#!/usr/bin/env python3
"""
PSP Sync — Synchronise les sauvegardes entre une vraie PSP et PPSSPP.
"""

import os
import shutil
import time
import threading
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────

PSP_VOLUME = "/Volumes/PSP"
PSP_SAVEDATA = os.path.join(PSP_VOLUME, "PSP", "SAVEDATA")
PPSSPP_MEMSTICK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PPSSPP-PSP")
PPSSPP_SAVEDATA = os.path.join(PPSSPP_MEMSTICK, "PSP", "SAVEDATA")

# ─── Colors ──────────────────────────────────────────────────────────────────

BG       = "#1A1A2E"
BG_CARD  = "#232342"
ACCENT   = "#6C5CE7"
ACCENT_H = "#7D6FF0"
SUCCESS  = "#00B894"
DANGER   = "#E17055"
TEXT     = "#FFFFFF"
TEXT_DIM = "#8888AA"

# ─── Sync Logic ──────────────────────────────────────────────────────────────

def is_psp_connected():
    return os.path.isdir(PSP_SAVEDATA)

def count_saves(path):
    if not os.path.isdir(path):
        return 0
    return len([d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))])

def sync_savedata(src, dst):
    os.makedirs(dst, exist_ok=True)
    copied, skipped, errors = [], [], []
    if not os.path.isdir(src):
        return copied, skipped, [f"Source introuvable : {src}"]
    for name in sorted(os.listdir(src)):
        src_f = os.path.join(src, name)
        dst_f = os.path.join(dst, name)
        if not os.path.isdir(src_f):
            continue
        try:
            src_files = [f for f in os.listdir(src_f) if os.path.isfile(os.path.join(src_f, f))]
            src_mt = max((os.path.getmtime(os.path.join(src_f, f)) for f in src_files), default=0)
            dst_mt = 0
            if os.path.isdir(dst_f):
                dst_files = [f for f in os.listdir(dst_f) if os.path.isfile(os.path.join(dst_f, f))]
                dst_mt = max((os.path.getmtime(os.path.join(dst_f, f)) for f in dst_files), default=0)
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

# ─── Rounded rectangle helper ───────────────────────────────────────────────

def round_rect(canvas, x1, y1, x2, y2, r=20, **kwargs):
    points = [
        x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r,
        x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2,
        x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r,
        x1, y1+r, x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, **kwargs)

# ─── App ─────────────────────────────────────────────────────────────────────

class PSPSyncApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PSP Sync")
        self.root.geometry("500x640")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        # Fonts
        self.font_title = tkfont.Font(family="Helvetica Neue", size=24, weight="bold")
        self.font_btn = tkfont.Font(family="Helvetica Neue", size=15, weight="bold")
        self.font_label = tkfont.Font(family="Helvetica Neue", size=12)
        self.font_big = tkfont.Font(family="Helvetica Neue", size=22, weight="bold")
        self.font_log = tkfont.Font(family="Menlo", size=11)

        self._build()
        self._update_status()

    def _build(self):
        root = self.root

        # ── Header ──
        hdr = tk.Frame(root, bg=BG)
        hdr.pack(fill="x", padx=30, pady=(25, 0))

        tk.Label(hdr, text="PSP Sync", font=self.font_title, fg=TEXT, bg=BG).pack(side="left")

        status_fr = tk.Frame(hdr, bg=BG)
        status_fr.pack(side="right")
        self.status_dot = tk.Label(status_fr, text="\u25CF", font=("Helvetica", 14), fg=DANGER, bg=BG)
        self.status_dot.pack(side="right", padx=(4, 0))
        self.status_lbl = tk.Label(status_fr, text="PSP déconnectée", font=self.font_label, fg=TEXT_DIM, bg=BG)
        self.status_lbl.pack(side="right")

        # ── Sep ──
        tk.Frame(root, bg="#333355", height=1).pack(fill="x", padx=30, pady=(18, 18))

        # ── Info cards ──
        cards = tk.Frame(root, bg=BG)
        cards.pack(fill="x", padx=30)

        self.psp_count = self._card(cards, "PSP", "—", side="left")
        self.pc_count = self._card(cards, "PPSSPP", "—", side="right")

        # ── Buttons ──
        btn_area = tk.Frame(root, bg=BG)
        btn_area.pack(fill="x", padx=30, pady=(22, 0))

        self.btn_pull = self._make_button(btn_area, "PSP  \u2192  PC", ACCENT, self._pull)
        self.btn_pull.pack(fill="x", pady=(0, 10))

        self.btn_push = self._make_button(btn_area, "PC  \u2192  PSP", "#3A3A5C", self._push)
        self.btn_push.pack(fill="x")

        # ── Log ──
        log_fr = tk.Frame(root, bg=BG_CARD, bd=0, highlightthickness=0)
        log_fr.pack(fill="both", expand=True, padx=30, pady=(18, 25))

        self.log = tk.Text(
            log_fr, bg=BG_CARD, fg="#CCCCDD", font=self.font_log,
            bd=0, highlightthickness=0, wrap="word", padx=10, pady=10,
            insertbackground=BG_CARD, cursor="arrow"
        )
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")
        self._log("En attente…")

    def _card(self, parent, title, value, side):
        fr = tk.Frame(parent, bg=BG_CARD, padx=16, pady=10)
        fr.pack(side=side, expand=True, fill="both", padx=(0 if side == "left" else 4, 4 if side == "left" else 0))
        tk.Label(fr, text=title, font=self.font_label, fg=TEXT_DIM, bg=BG_CARD, anchor="w").pack(fill="x")
        lbl = tk.Label(fr, text=value, font=self.font_big, fg=TEXT, bg=BG_CARD, anchor="w")
        lbl.pack(fill="x", pady=(2, 0))
        return lbl

    def _make_button(self, parent, text, color, cmd):
        btn = tk.Button(
            parent, text=text, font=self.font_btn,
            fg=TEXT, bg=color, activebackground=ACCENT_H, activeforeground=TEXT,
            bd=0, highlightthickness=0, relief="flat",
            height=2, cursor="hand2", command=cmd
        )
        return btn

    def _log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.configure(state="normal")
        self.log.insert("end", f"[{ts}]  {msg}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _update_status(self):
        connected = is_psp_connected()
        if connected:
            self.status_dot.configure(fg=SUCCESS)
            self.status_lbl.configure(text="PSP connectée")
            self.psp_count.configure(text=f"{count_saves(PSP_SAVEDATA)} saves")
            self.btn_pull.configure(state="normal")
            self.btn_push.configure(state="normal")
        else:
            self.status_dot.configure(fg=DANGER)
            self.status_lbl.configure(text="PSP déconnectée")
            self.psp_count.configure(text="—")
            self.btn_pull.configure(state="disabled")
            self.btn_push.configure(state="disabled")
        pc = count_saves(PPSSPP_SAVEDATA)
        self.pc_count.configure(text=f"{pc} saves" if pc else "—")
        self.root.after(2000, self._update_status)

    def _set_busy(self, busy):
        s = "disabled" if busy else "normal"
        self.btn_pull.configure(state=s)
        self.btn_push.configure(state=s)

    def _pull(self):
        if not is_psp_connected():
            self._log("PSP non détectée !")
            return
        self._set_busy(True)
        self._log("Sync PSP → PC…")
        threading.Thread(target=self._sync, args=(PSP_SAVEDATA, PPSSPP_SAVEDATA, "PSP → PC"), daemon=True).start()

    def _push(self):
        if not is_psp_connected():
            self._log("PSP non détectée !")
            return
        self._set_busy(True)
        self._log("Sync PC → PSP…")
        threading.Thread(target=self._sync, args=(PPSSPP_SAVEDATA, PSP_SAVEDATA, "PC → PSP"), daemon=True).start()

    def _sync(self, src, dst, label):
        t0 = time.time()
        copied, skipped, errors = sync_savedata(src, dst)
        dt = time.time() - t0
        def update():
            if copied:
                self._log(f"{label} — {len(copied)} save(s) copiée(s) ({dt:.1f}s)")
                for n in copied:
                    self._log(f"   {n}")
            if skipped:
                self._log(f"{len(skipped)} save(s) déjà à jour")
            if errors:
                for e in errors:
                    self._log(f"ERREUR: {e}")
            if not copied and not errors:
                self._log(f"{label} — Tout synchronisé")
            self._set_busy(False)
        self.root.after(0, update)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    PSPSyncApp().run()
