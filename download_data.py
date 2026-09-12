#!/usr/bin/env python3
"""Download the official MaleCNS v1.0 structural release (not functional weights).

Standard-library only. Resumes partial downloads, checks server-provided MD5 when
available, and records local SHA-256. Never fabricates data after a failed request.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/"
FILES = {
    "weights": "connectome-weights-male-cns-v1.0-minconf-0.5.feather",
    "annotations": "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    "neurotransmitters": "body-neurotransmitters-male-cns-v1.0.feather",
    "stats": "body-stats-male-cns-v1.0-minconf-0.5.feather",
    "points": "syn-points-male-cns-v1.0-minconf-0.5.feather",
    "partners": "syn-partners-male-cns-v1.0-minconf-0.5.feather",
    "tbar_neurotransmitters": "tbar-neurotransmitters-male-cns-v1.0.feather",
}
PROFILES = {
    "core": ["annotations", "neurotransmitters", "weights"],
    "all-tables": list(FILES),
}


def hashes(path: Path) -> tuple[str, str]:
    sha, md5 = hashlib.sha256(), hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), base64.b64encode(md5.digest()).decode("ascii")


def atomic_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def header_metadata(headers) -> tuple[int | None, str | None]:
    length = headers.get("Content-Length")
    size = int(length) if length is not None else None
    md5 = None
    fields = headers.get_all("x-goog-hash", []) if hasattr(headers, "get_all") else [headers.get("x-goog-hash", "")]
    for field in ",".join(fields).split(","):
        field = field.strip()
        if field.startswith("md5="):
            md5 = field[4:]
    return size, md5


def valid_feather_magic(path: Path) -> bool:
    if path.stat().st_size < 12:
        return False
    with path.open("rb") as f:
        head = f.read(6)
        f.seek(-6, 2)
        tail = f.read(6)
    return (head == b"ARROW1" and tail == b"ARROW1") or (
        head[:4] == b"FEA1" and tail[-4:] == b"FEA1"
    )


def download(key: str, out: Path, retries: int = 5) -> dict:
    url = BASE + FILES[key]
    final = out / FILES[key]
    partial = final.with_suffix(final.suffix + ".part")
    expected_size, expected_md5 = None, None
    # HEAD may be disallowed by proxies. GET headers remain a fallback.
    try:
        request = urllib.request.Request(url, method="HEAD", headers={"Accept-Encoding": "identity"})
        with urllib.request.urlopen(request, timeout=60) as r:
            expected_size, expected_md5 = header_metadata(r.headers)
    except (OSError, urllib.error.URLError):
        pass

    if final.exists():
        sha, md5 = hashes(final)
        receipt = final.with_suffix(final.suffix + ".receipt.json")
        local_verified = False
        if receipt.exists():
            previous = json.loads(receipt.read_text(encoding="utf-8"))
            local_verified = previous.get("sha256") == sha and previous.get("url") == url
        remote_verified = expected_md5 is not None and md5 == expected_md5
        size_ok = expected_size is None or final.stat().st_size == expected_size
        if (local_verified or remote_verified) and size_ok and valid_feather_magic(final):
            print(f"Verified existing: {final.name}", flush=True)
            return {"url": url, "file": final.name, "bytes": final.stat().st_size,
                    "sha256": sha, "server_md5_verified": remote_verified,
                    "status": "verified-existing"}
        raise RuntimeError(f"Existing file is unverified or corrupt: {final}. Move it aside and retry.")

    for attempt in range(retries):
        offset = partial.stat().st_size if partial.exists() else 0
        if expected_size is not None and offset == expected_size:
            break
        headers = {"Accept-Encoding": "identity", "User-Agent": "MaleCNS-language-lab/0.1"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as r:
                status = r.status
                size, remote_md5 = header_metadata(r.headers)
                expected_md5 = remote_md5 or expected_md5
                if status == 206:
                    cr = r.headers.get("Content-Range", "")
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", cr)
                    if match is None or int(match[1]) != offset:
                        raise RuntimeError(f"Unexpected Content-Range: {cr}")
                    expected_size = int(match[3])
                elif status == 200:
                    offset = 0  # Server ignored Range: restart rather than append.
                    expected_size = size if size is not None else expected_size
                else:
                    raise RuntimeError(f"Unexpected HTTP status {status}")
                with partial.open("ab" if offset else "wb") as f:
                    written, last_print = offset, time.monotonic()
                    for block in iter(lambda: r.read(4 * 1024 * 1024), b""):
                        f.write(block)
                        written += len(block)
                        if time.monotonic() - last_print > 5:
                            print(f"{final.name}: {written / 1e6:.1f} MB", flush=True)
                            last_print = time.monotonic()
            if expected_size is not None and partial.stat().st_size != expected_size:
                raise OSError("Incomplete transfer; the next attempt will resume it")
            break
        except (OSError, urllib.error.URLError) as exc:
            if attempt + 1 == retries:
                raise RuntimeError(f"Download failed; partial file retained: {partial}") from exc
            time.sleep(min(2 ** attempt, 16))
    if not partial.exists() or not valid_feather_magic(partial):
        raise RuntimeError("Not a valid Feather/Arrow file; data has NOT been accepted")
    if expected_size is not None and partial.stat().st_size != expected_size:
        raise RuntimeError("Byte count mismatch")
    sha, md5 = hashes(partial)
    if expected_md5 is not None and md5 != expected_md5:
        raise RuntimeError(f"Server MD5 mismatch: {partial}; remove the partial file and retry")
    partial.replace(final)
    record = {"url": url, "file": final.name, "bytes": final.stat().st_size,
              "sha256": sha, "server_md5_verified": expected_md5 is not None,
              "status": "downloaded", "retrieved_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(final.with_suffix(final.suffix + ".receipt.json"), record)
    return record


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=Path("data/raw"))
    p.add_argument("--profile", choices=PROFILES, default="core")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.dry_run:
        for key in PROFILES[args.profile]:
            print(BASE + FILES[key])
        return
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = {"dataset": "male-cns:v1.0", "release_minconf": 0.5,
                "meaning": "structural connectome, NOT measured functional synaptic weights",
                "data_license": "CC-BY (see official release)", "files": []}
    path = args.out / "download_manifest.json"
    for key in PROFILES[args.profile]:
        manifest["files"].append(download(key, args.out))
        atomic_json(path, manifest)
    print(f"Completed: {path}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
