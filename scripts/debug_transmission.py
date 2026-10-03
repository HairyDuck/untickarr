"""
One-off script to see what Transmission RPC returns for torrents (labels + files).
Run from repo root: python scripts/debug_transmission.py
"""
import json
import os
import sys

# Add project root so we can use app or run standalone
sys.path.insert(0, ".")

import transmission_rpc

HOST = os.environ.get("TRANSMISSION_HOST", "127.0.0.1")
PORT = int(os.environ.get("TRANSMISSION_PORT", "9091"))
PATH = os.environ.get("TRANSMISSION_PATH", "/transmission/rpc")
USER = os.environ.get("TRANSMISSION_USER", "admin")
PASS = os.environ.get("TRANSMISSION_PASS", "admin")
FIELDS = ["id", "name", "labels", "group", "category", "files", "priorities", "wanted"]

def main():
    print(f"Connecting to {HOST}:{PORT} ({PATH}) as {USER}...")
    client = transmission_rpc.Client(
        host=HOST,
        port=PORT,
        path=PATH,
        protocol="http",
        username=USER,
        password=PASS,
    )
    print("Connected.\n")

    # Get torrents with same fields as the app
    torrents = client.get_torrents(arguments=FIELDS)
    print(f"get_torrents(arguments={FIELDS}) returned {len(torrents)} torrent(s).\n")

    for t in torrents:
        print("=" * 60)
        print(f"Torrent id={getattr(t, 'id', None)} name={getattr(t, 'name', None)!r}")
        # Labels / group / category (vendor-dependent)
        for attr in ("labels", "group", "category"):
            val = getattr(t, attr, None)
            print(f"  {attr}: {val!r} (type={type(val).__name__})")
        # Raw dict if the library stores it
        if hasattr(t, "_fields") or hasattr(t, "__dict__"):
            d = getattr(t, "_fields", None) or getattr(t, "__dict__", None)
            if d and isinstance(d, dict):
                print(f"  _fields/raw keys: {list(d.keys())}")
        # File list
        try:
            files = t.get_files()
            file_list = list(files) if files is not None else []
            print(f"  get_files(): {len(file_list)} file(s)")
            for i, f in enumerate(file_list):
                fid = getattr(f, "id", None)
                fname = getattr(f, "name", None)
                print(f"    [{i}] id={fid!r} name={fname!r}")
                if hasattr(f, "_fields"):
                    print(f"        _fields: {f._fields}")
        except Exception as e:
            print(f"  get_files() error: {e}")
        print()

if __name__ == "__main__":
    main()
