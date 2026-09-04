#!/usr/bin/env bash

set -euo pipefail

usage() {
  echo "Usage: $0 {major|minor|patch}" >&2
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

bump_type="$1"
case "$bump_type" in
  major | minor | patch) ;;
  *)
    usage
    exit 2
    ;;
esac

for command_name in uv node npm; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Error: required command '$command_name' was not found." >&2
    exit 1
  fi
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
package_json="$script_dir/frontend/package.json"

python_version="$(uv version --project "$script_dir" --short)"
frontend_version="$(node -p 'require(process.argv[1]).version' "$package_json")"

if [[ "$python_version" != "$frontend_version" ]]; then
  echo "Error: project versions do not match (pyproject.toml: $python_version, package.json: $frontend_version)." >&2
  exit 1
fi

new_version="$(uv version --project "$script_dir" --no-sync --short --bump "$bump_type")"
npm pkg set "version=$new_version" --prefix "$script_dir/frontend"

echo "Version bumped from $python_version to $new_version."
