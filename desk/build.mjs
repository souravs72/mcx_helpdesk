#!/usr/bin/env node
/**
 * Build Helpdesk desk assets with MCX UI overrides (helpdesk source unchanged).
 */
import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HELPDESK_DESK = path.resolve(__dirname, "../../helpdesk/desk");
const STAGING_DIR = path.join(HELPDESK_DESK, ".mcx-ui-staging");
const VITE_CONFIG = path.resolve(__dirname, "vite.config.cjs");

if (!fs.existsSync(HELPDESK_DESK)) {
	console.error("Helpdesk app not found alongside mcx_helpdesk in bench apps/");
	process.exit(1);
}

if (!fs.existsSync(path.join(HELPDESK_DESK, "node_modules"))) {
	console.log("Installing Helpdesk desk dependencies...");
	execSync("yarn install", { cwd: HELPDESK_DESK, stdio: "inherit" });
}

console.log("Building Helpdesk desk with MCX UI overrides...");
try {
	execSync(`yarn vite build --config "${VITE_CONFIG}"`, {
		cwd: HELPDESK_DESK,
		stdio: "inherit",
	});
	console.log("MCX Helpdesk desk build complete.");
} finally {
	fs.rmSync(STAGING_DIR, { recursive: true, force: true });
}
