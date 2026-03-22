# PSP Sync

Sync save data between a real PSP and PPSSPP — works on macOS, Linux, and Windows.

## What it does

- **PSP → PC** : Copy saves from your PSP to your computer before playing on PPSSPP
- **PC → PSP** : Send saves back to your PSP when you're done
- Smart sync: only copies saves that are newer than the destination
- Auto-detects your PSP when plugged in via USB

## Requirements

- Python 3 (tkinter included by default)
- A PSP connected in USB mode (shows up as a drive)

## Launch

```bash
python3 pspsync.py
```

That's it. No compilation, no install, no dependencies.

## How it works

| OS | PSP detection | PPSSPP saves |
|---|---|---|
| macOS | `/Volumes/PSP` | `./PPSSPP-PSP/PSP/SAVEDATA/` |
| Linux | `/media/*/PSP` or `/mnt/PSP` | `./PPSSPP-PSP/PSP/SAVEDATA/` |
| Windows | Scans drive letters (D:\, E:\, ...) | `./PPSSPP-PSP/PSP/SAVEDATA/` |

PPSSPP saves are stored next to the script in `PPSSPP-PSP/PSP/SAVEDATA/`. Point PPSSPP to this folder as its memstick directory.

## macOS .app (optional)

```bash
pip3 install py2app
python3 setup.py py2app -A
open dist/PSP\ Sync.app
```

---

*Made by [Noème](https://github.com/romainguerif)*
