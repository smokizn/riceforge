#!/usr/bin/env bash
# Run every safe test. None of them touch the live desktop, system services,
# packages or network: see tests/lib.sh for how the sandbox works.
# Disruptive hardware tests (Wi-Fi/Bluetooth reconnects) are separate and opt-in:
# shell/tests/test_disruptive.py.
cd "$(dirname "$0")/.." || exit 1
rc=0
run() { printf '\n════ %s\n' "$1"; shift; "$@" || { rc=1; printf '════ FAILED: %s\n' "$*"; }; }
run "static checks"              python3 -I tests/check_static.py
run "shell logic (astro, wifi, bluetooth)" python3 -I shell/tests/test_logic.py
run "installer"                  bash tests/test_install.sh
run "themes and sessions"        bash tests/test_themes.sh
run "hardware and dependencies"  bash tests/test_hardware.sh
printf '\n%s\n' "$([[ $rc == 0 ]] && echo 'ALL SUITES PASSED' || echo 'SOME SUITES FAILED')"
exit $rc
