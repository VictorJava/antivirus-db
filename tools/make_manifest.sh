#!/usr/bin/env bash
# Writes manifest.json for the database files in a directory.
# Usage: tools/make_manifest.sh <dir> <version> <generated_at ISO-8601>
set -euo pipefail
DIR="${1:?dir}"; VERSION="${2:?version}"; GEN="${3:?generated_at}"
# Cross-platform stat helpers (GNU vs BSD)
if stat --version >/dev/null 2>&1; then
  file_mtime() { stat -c %Y "$1"; }
  file_size()  { stat -c %s "$1"; }
  fmt_epoch()  { date -u -d "@$1" "$2"; }
else
  file_mtime() { stat -f %m "$1"; }
  file_size()  { stat -f %z "$1"; }
  fmt_epoch()  { date -u -r "$1" "$2"; }
fi
FILES=(hypatia-md5-bloom.bin hypatia-sha1-bloom.bin hypatia-sha256-bloom.bin)
{
  echo "{"
  echo "  \"schema\": 1,"
  echo "  \"version\": \"$VERSION\","
  echo "  \"generated_at\": \"$GEN\","
  echo "  \"min_app_version_code\": 1,"
  echo "  \"signature_count\": 0,"
  echo "  \"files\": ["
  for i in "${!FILES[@]}"; do
    f="${FILES[$i]}"
    size=$(file_size "$DIR/$f")
    sha=$(shasum -a 256 "$DIR/$f" | cut -d' ' -f1)
    sep=","; [[ $i -eq $((${#FILES[@]}-1)) ]] && sep=""
    echo "    { \"name\": \"$f\", \"size\": $size, \"sha256\": \"$sha\" }$sep"
  done
  echo "  ]"
  echo "}"
} > "$DIR/manifest.json"
cat "$DIR/manifest.json"
