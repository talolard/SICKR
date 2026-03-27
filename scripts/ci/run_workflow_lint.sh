#!/usr/bin/env bash
set -euo pipefail

repo_root="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd
)"
tools_root="${repo_root}/.tmp_untracked/tooling"

actionlint_version="1.7.11"
shellcheck_version="0.10.0"

ensure_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "${command_name}" >&2
    exit 1
  fi
}

actionlint_asset_name() {
  local os_name="$1"
  local arch_name="$2"

  case "${os_name}/${arch_name}" in
    darwin/arm64)
      printf 'actionlint_%s_darwin_arm64.tar.gz\n' "${actionlint_version}"
      ;;
    darwin/x86_64)
      printf 'actionlint_%s_darwin_amd64.tar.gz\n' "${actionlint_version}"
      ;;
    linux/aarch64 | linux/arm64)
      printf 'actionlint_%s_linux_arm64.tar.gz\n' "${actionlint_version}"
      ;;
    linux/x86_64 | linux/amd64)
      printf 'actionlint_%s_linux_amd64.tar.gz\n' "${actionlint_version}"
      ;;
    *)
      printf 'Unsupported platform for actionlint: %s/%s\n' "${os_name}" "${arch_name}" >&2
      exit 1
      ;;
  esac
}

shellcheck_asset_name() {
  local os_name="$1"
  local arch_name="$2"

  case "${os_name}/${arch_name}" in
    darwin/arm64)
      printf 'shellcheck-v%s.darwin.aarch64.tar.xz\n' "${shellcheck_version}"
      ;;
    darwin/x86_64)
      printf 'shellcheck-v%s.darwin.x86_64.tar.xz\n' "${shellcheck_version}"
      ;;
    linux/aarch64 | linux/arm64)
      printf 'shellcheck-v%s.linux.aarch64.tar.xz\n' "${shellcheck_version}"
      ;;
    linux/x86_64 | linux/amd64)
      printf 'shellcheck-v%s.linux.x86_64.tar.xz\n' "${shellcheck_version}"
      ;;
    *)
      printf 'Unsupported platform for shellcheck: %s/%s\n' "${os_name}" "${arch_name}" >&2
      exit 1
      ;;
  esac
}

install_actionlint() {
  local os_name="$1"
  local arch_name="$2"
  local install_dir="${tools_root}/actionlint/v${actionlint_version}"
  local binary_path="${install_dir}/actionlint"
  local archive_name
  local archive_path
  local temp_dir

  if [[ -x "${binary_path}" ]]; then
    printf '%s\n' "${binary_path}"
    return
  fi

  mkdir -p "${install_dir}"
  archive_name="$(actionlint_asset_name "${os_name}" "${arch_name}")"
  archive_path="${tools_root}/${archive_name}"
  temp_dir="$(mktemp -d)"

  curl -fsSL \
    "https://github.com/rhysd/actionlint/releases/download/v${actionlint_version}/${archive_name}" \
    -o "${archive_path}"
  tar -xzf "${archive_path}" -C "${temp_dir}"
  cp "${temp_dir}/actionlint" "${binary_path}"
  chmod +x "${binary_path}"
  rm -rf "${temp_dir}"

  printf '%s\n' "${binary_path}"
}

install_shellcheck() {
  local os_name="$1"
  local arch_name="$2"
  local install_dir="${tools_root}/shellcheck/v${shellcheck_version}"
  local binary_path="${install_dir}/shellcheck"
  local archive_name
  local archive_path
  local temp_dir

  if [[ -x "${binary_path}" ]]; then
    printf '%s\n' "${binary_path}"
    return
  fi

  mkdir -p "${install_dir}"
  archive_name="$(shellcheck_asset_name "${os_name}" "${arch_name}")"
  archive_path="${tools_root}/${archive_name}"
  temp_dir="$(mktemp -d)"

  curl -fsSL \
    "https://github.com/koalaman/shellcheck/releases/download/v${shellcheck_version}/${archive_name}" \
    -o "${archive_path}"
  tar -xJf "${archive_path}" -C "${temp_dir}"
  cp "${temp_dir}/shellcheck-v${shellcheck_version}/shellcheck" "${binary_path}"
  chmod +x "${binary_path}"
  rm -rf "${temp_dir}"

  printf '%s\n' "${binary_path}"
}

main() {
  local os_name
  local arch_name
  local actionlint_bin
  local shellcheck_bin

  ensure_command curl
  ensure_command tar

  os_name="$(uname -s | tr '[:upper:]' '[:lower:]')"
  arch_name="$(uname -m)"

  mkdir -p "${tools_root}"
  actionlint_bin="$(install_actionlint "${os_name}" "${arch_name}")"
  shellcheck_bin="$(install_shellcheck "${os_name}" "${arch_name}")"

  (
    cd "${repo_root}"
    PATH="$(dirname "${shellcheck_bin}"):${PATH}" "${actionlint_bin}" -color
  )
}

main "$@"
