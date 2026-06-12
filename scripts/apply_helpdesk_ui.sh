#!/usr/bin/env bash
# Apply MCX Helpdesk UI overrides onto the Frappe Helpdesk app source tree.
# Run from bench root after `bench get-app` / git pull on mcx_helpdesk.
set -euo pipefail

BENCH_ROOT="${1:-$(pwd)}"
MCX_APP="${BENCH_ROOT}/apps/mcx_helpdesk"
HELPDESK_APP="${BENCH_ROOT}/apps/helpdesk"
OVERRIDES="${MCX_APP}/overrides/helpdesk"

if [[ ! -d "${OVERRIDES}/desk" ]]; then
	echo "No Helpdesk UI overrides found at ${OVERRIDES}"
	exit 1
fi

if [[ ! -d "${HELPDESK_APP}/desk" ]]; then
	echo "Helpdesk app not found at ${HELPDESK_APP}"
	exit 1
fi

echo "Applying Helpdesk UI overrides from mcx_helpdesk..."
cp -a "${OVERRIDES}/desk/." "${HELPDESK_APP}/desk/"
echo "Done. Run: bench build --app helpdesk"
