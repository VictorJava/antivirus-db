#!/usr/bin/env python3
"""
Builds the dangerous-link database used by the app's link protection.

Sources (all allow commercial use):
  - URLhaus via malware-filter/urlhaus-filter (CC0 / MIT): malware domains and full URLs
  - Phishing.Database (MIT): phishing domains
Popular domains (Tranco top list, MIT) and tools/link_allowlist.txt are never put on the domain list, so a
malicious file on github.com only matches by its full URL, never blocks github.com itself.

Output (into <out-dir>):
  link-domains.bin, link-urls.bin   "AVLK" | u8 format=1 | u8 kind (1 domains, 2 urls) | u32 count | count x i64 (sorted)
  links-manifest.json               version, generated_at, counts, sizes and sha256 of the files

Each entry is the first 8 bytes of SHA-256 of the normalized key, as a signed big-endian 64-bit number:
  domain key: lowercase IDNA host without "www." and trailing dot           e.g. "evil.example"
  url key:    domain key + path (+ "?" + query), trailing "/" removed         e.g. "evil.example/a/b.apk"
The app (core/links/LinkKeys.kt) normalizes the same way. Keep both in sync.

Usage: tools/build_link_db.py <out-dir> [--allow-top N]
"""
import argparse, datetime, hashlib, io, json, os, struct, sys, urllib.request, zipfile

URLHAUS = "https://malware-filter.gitlab.io/malware-filter/urlhaus-filter-online.txt"
PHISHING_DB = "https://raw.githubusercontent.com/Phishing-Database/Phishing.Database/master/phishing-domains-ACTIVE.txt"
TRANCO = "https://tranco-list.eu/top-1m.csv.zip"
UA = {"User-Agent": "antivirus-link-db-builder/1.0"}
# Self-test entries (like Hypatia's test signatures): harmless addresses under example.com/.org that are always
# on the lists, so the app's link protection can be tried safely. See test-files/test-links.md.
# shield-blocked-test.127.0.0.1.nip.io really resolves (to the phone itself, 127.0.0.1), so it shows that Web
# protection blocks a name that exists; example.com subdomains don't exist and fail even without protection.
TEST_DOMAINS = {"shield-phishing-test.example.com", "shield-blocked-test.127.0.0.1.nip.io"}
TEST_URLS = {"example.org/shield-malware-test.apk"}


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def norm_host(h: str) -> str | None:
    h = h.strip().lower().rstrip(".")
    if not h or " " in h or "/" in h:
        return None
    if ":" in h and not h.startswith("["):
        h = h.split(":", 1)[0]
    try:
        h = h.encode("idna").decode("ascii")
    except Exception:
        return None
    if h.startswith("www."):
        h = h[4:]
    return h or None


def norm_url(u: str) -> str | None:
    u = u.strip()
    if "://" in u:
        u = u.split("://", 1)[1]
    u = u.split("#", 1)[0]
    host, sep, rest = u.partition("/")
    host = host.rsplit("@", 1)[-1]
    h = norm_host(host)
    if not h:
        return None
    path = "/" + rest if sep else ""
    path = path.rstrip("/")
    return h + path


def key64(s: str) -> int:
    return struct.unpack(">q", hashlib.sha256(s.encode("utf-8")).digest()[:8])[0]


def write_bin(path: str, kind: int, keys: set[str]) -> int:
    values = sorted({key64(k) for k in keys})
    with open(path, "wb") as f:
        f.write(b"AVLK" + struct.pack(">BBI", 1, kind, len(values)))
        f.write(b"".join(struct.pack(">q", v) for v in values))
    return len(values)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--allow-top", type=int, default=20000, help="exclude the N most popular domains (Tranco)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    allow: set[str] = set()
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "link_allowlist.txt"), encoding="utf-8") as f:
        allow |= {h for h in (norm_host(l) for l in f if l.strip() and not l.startswith("#")) if h}
    try:
        z = zipfile.ZipFile(io.BytesIO(fetch(TRANCO)))
        for i, line in enumerate(z.read(z.namelist()[0]).decode().splitlines()):
            if i >= a.allow_top:
                break
            h = norm_host(line.split(",", 1)[1])
            if h:
                allow.add(h)
    except Exception as e:  # the hand-made allowlist still applies
        print(f"WARNING: Tranco list not loaded ({e})", file=sys.stderr)

    domains: set[str] = set()
    urls: set[str] = set()
    for line in fetch(URLHAUS).decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line or line.startswith("!") or line.startswith("#"):
            continue
        line = line.removeprefix("||").split("^", 1)[0]
        if "/" in line:
            u = norm_url(line)
            if u:
                urls.add(u)
        else:
            h = norm_host(line)
            if h:
                domains.add(h)
    malware_domains = len(domains)
    for line in fetch(PHISHING_DB).decode("utf-8", "replace").splitlines():
        if line and not line.startswith("#"):
            h = norm_host(line)
            if h:
                domains.add(h)
    blocked = {d for d in domains if d not in allow} | TEST_DOMAINS
    urls |= TEST_URLS
    removed = len(domains) - len(blocked)

    n_dom = write_bin(os.path.join(a.out, "link-domains.bin"), 1, blocked)
    n_url = write_bin(os.path.join(a.out, "link-urls.bin"), 2, urls)
    now = datetime.datetime.now(datetime.timezone.utc)
    files = []
    for name in ("link-domains.bin", "link-urls.bin"):
        p = os.path.join(a.out, name)
        files.append({"name": name, "size": os.path.getsize(p), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest()})
    manifest = {
        "schema": 1,
        "version": now.strftime("%Y.%m.%d.%H%M"),
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domain_count": n_dom,
        "url_count": n_url,
        "sources": ["URLhaus (malware-filter mirror, CC0)", "Phishing.Database (MIT)"],
        "files": files,
    }
    with open(os.path.join(a.out, "links-manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"domains: {n_dom} (malware {malware_domains}, popular removed {removed}), urls: {n_url}, version {manifest['version']}")


if __name__ == "__main__":
    main()
