#!/usr/bin/env bash
# Build Helpdesk desk assets with MCX UI overrides (does NOT modify helpdesk source).
# Prefer: bench build --app mcx_helpdesk
set -euo pipefail

BENCH_ROOT="${1:-$(pwd)}"
MCX_APP="${BENCH_ROOT}/apps/mcx_helpdesk"

if [[ ! -f "${MCX_APP}/desk/build.mjs" ]]; then
	echo "MCX Helpdesk desk build not found at ${MCX_APP}/desk/"
	exit 1
fi

echo "Building Helpdesk UI via mcx_helpdesk overrides (helpdesk source unchanged)..."
(cd "${MCX_APP}" && yarn build)
echo "Done. Helpdesk desk assets updated under apps/helpdesk/helpdesk/public/desk/"
