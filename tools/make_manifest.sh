#!/usr/bin/env bash
# Writes manifest.json for the database files in a directory.
# Usage: tools/make_manifest.sh <dir> <version> <generated_at ISO-8601>
set -euo pipefail
DIR="${1:?dir}"; VERSION="${2:?version}"; GEN="${3:?generated_at}"
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
    size=$(stat -f %z "$DIR/$f" 2>/dev/null || stat -c %s "$DIR/$f")
    sha=$(shasum -a 256 "$DIR/$f" | cut -d' ' -f1)
    sep=","; [[ $i -eq $((${#FILES[@]}-1)) ]] && sep=""
    echo "    { \"name\": \"$f\", \"size\": $size, \"sha256\": \"$sha\" }$sep"
  done
  echo "  ]"
  echo "}"
} > "$DIR/manifest.json"
cat "$DIR/manifest.json"
