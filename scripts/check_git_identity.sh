#!/usr/bin/env bash
set -euo pipefail

expected_name="Tal Perry"
expected_email="talolard@gmail.com"

actual_name="$(git config --local user.name || true)"
actual_email="$(git config --local user.email || true)"

if [[ "${actual_name}" != "${expected_name}" ]]; then
  printf 'FAIL: git user.name is "%s" (expected "%s")\n' "${actual_name}" "${expected_name}"
  exit 1
fi

if [[ "${actual_email}" != "${expected_email}" ]]; then
  printf 'FAIL: git user.email is "%s" (expected "%s")\n' "${actual_email}" "${expected_email}"
  exit 1
fi

printf 'OK: git identity matches expected public profile.\n'
