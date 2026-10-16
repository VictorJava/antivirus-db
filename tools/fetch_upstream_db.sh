#!/usr/bin/env bash
# Downloads the latest Hypatia-compatible databases from the MaintainTeam mirror,
# verifies their detached GPG signatures and writes manifest.json.
# Usage: tools/fetch_upstream_db.sh <output-dir>
set -euo pipefail
OUT="${1:?output dir}"
BASE="${UPSTREAM_BASE:-https://maintainteam.github.io/HypatiaDatabases/}"
KEY_ID="${UPSTREAM_KEY_ID:-5298C0C0C3E73288}"
FILES=(hypatia-md5-bloom.bin hypatia-sha1-bloom.bin hypatia-sha256-bloom.bin)
mkdir -p "$OUT"
curl -fsSL -o "$OUT/gpg.key" "${BASE}gpg.key"
newest=0
for f in "${FILES[@]}"; do
  curl -fsSL -R -o "$OUT/$f" "${BASE}$f"
  curl -fsSL -o "$OUT/$f.sig" "${BASE}$f.sig"
  lm=$(stat -f %m "$OUT/$f" 2>/dev/null || stat -c %Y "$OUT/$f")
  (( lm > newest )) && newest=$lm
done
if command -v gpg >/dev/null; then
  export GNUPGHOME="$(mktemp -d)"
  gpg --quiet --import "$OUT/gpg.key"
  for f in "${FILES[@]}"; do
    gpg --quiet --verify "$OUT/$f.sig" "$OUT/$f" 2>&1 | grep -q "$KEY_ID" || { echo "GPG verification failed for $f" >&2; exit 1; }
  done
  echo "GPG signatures OK"
else
  echo "WARNING: gpg not installed, signatures not verified" >&2
fi
GEN=$(date -u -r "$newest" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d "@$newest" +%Y-%m-%dT%H:%M:%SZ)
VERSION="${VERSION:-$(date -u -r "$newest" +%Y.%m.%d 2>/dev/null || date -u -d "@$newest" +%Y.%m.%d)}"
"$(dirname "$0")/make_manifest.sh" "$OUT" "$VERSION" "$GEN"
echo "Fetched $VERSION (generated $GEN) into $OUT"
