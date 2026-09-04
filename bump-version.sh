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

for command_name in git uv node; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Error: required command '$command_name' was not found." >&2
    exit 1
  fi
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
package_json="$script_dir/frontend/package.json"

if ! git -C "$script_dir" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: $script_dir is not inside a Git working tree." >&2
  exit 1
fi

modified_version_files="$(
  git -C "$script_dir" status --porcelain -- pyproject.toml uv.lock frontend/package.json
)"
if [[ -n "$modified_version_files" ]]; then
  echo "Error: version files contain uncommitted changes:" >&2
  echo "$modified_version_files" >&2
  exit 1
fi

python_version="$(uv version --project "$script_dir" --short)"
frontend_version="$(node -p 'require(process.argv[1]).version' "$package_json")"

if [[ "$python_version" != "$frontend_version" ]]; then
  echo "Error: project versions do not match (pyproject.toml: $python_version, package.json: $frontend_version)." >&2
  exit 1
fi

new_version="$(uv version --project "$script_dir" --no-sync --short --bump "$bump_type")"
node -e '
  const fs = require("fs");
  const path = process.argv[1];
  const version = process.argv[2];
  const packageJson = JSON.parse(fs.readFileSync(path, "utf8"));
  packageJson.version = version;
  fs.writeFileSync(path, `${JSON.stringify(packageJson, null, 2)}\n`);
' "$package_json" "$new_version"

echo "Version bumped from $python_version to $new_version."

commit_answer=""
read -r -p "Commit the version changes and create tag v$new_version? [y/N] " commit_answer || true
if [[ "$commit_answer" =~ ^[Yy]([Ee][Ss])?$ ]]; then
  tag_name="v$new_version"
  if git -C "$script_dir" rev-parse --quiet --verify "refs/tags/$tag_name" >/dev/null; then
    echo "Error: tag $tag_name already exists." >&2
    exit 1
  fi

  git -C "$script_dir" commit --only -m "Bump version to $new_version" -- \
    pyproject.toml uv.lock frontend/package.json
  git -C "$script_dir" tag "$tag_name"
  echo "Created commit and tag $tag_name."
else
  echo "Version files were not committed or tagged."
fi
