#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_root="${CORPUS_SOURCE_ROOT:-/Users/ava-sensas/Library/CloudStorage/Dropbox/AAA_LOGGRO Ongoing/AI/LIA_contadores/Corpus}"
snapshot_root="${CORPUS_SNAPSHOT_DIR:-$repo_root/knowledge_base}"

if [[ ! -d "$source_root" ]]; then
  echo "Corpus source root does not exist: $source_root" >&2
  exit 1
fi

mkdir -p "$snapshot_root"

for root_name in "CORE ya Arriba" "to upload"; do
  rm -rf "$snapshot_root/$root_name"
done

should_exclude() {
  local rel_lower="$1"
  case "$rel_lower" in
    *.ds_store) return 0 ;;
    */state.md|*/estado.md) return 0 ;;
    */readme.md|*/readme-*.md) return 0 ;;
    */claude.md|*/updator.md) return 0 ;;
    *audit-gap-analysis*|*analisis-gap*|*gap-analysis*) return 0 ;;
    *plan-aggrandizement*|*relaciones-cross-domain*|*vocabulario-canonico*) return 0 ;;
    *resumen*.txt|*summary*.txt) return 0 ;;
  esac
  return 1
}

tmp_file_list="$(mktemp)"
cleanup() {
  rm -f "$tmp_file_list"
}
trap cleanup EXIT

while IFS= read -r source_file; do
  rel_path="${source_file#"$source_root"/}"
  rel_lower="$(printf '%s' "$rel_path" | tr '[:upper:]' '[:lower:]')"
  if should_exclude "$rel_lower"; then
    continue
  fi
  printf '%s\n' "$rel_path" >> "$tmp_file_list"
done < <(
  find "$source_root/CORE ya Arriba" "$source_root/to upload" -type f | sort
)

rsync -aR --files-from="$tmp_file_list" "$source_root"/ "$snapshot_root"/

echo "Snapshot created at: $snapshot_root"
echo "Source root: $source_root"
echo "Copied files: $(wc -l < "$tmp_file_list" | tr -d ' ')"
