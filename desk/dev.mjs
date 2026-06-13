#!/usr/bin/env node
/** Dev server for Helpdesk desk with MCX UI overrides. */
import { execSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const HELPDESK_DESK = path.resolve(__dirname, "../../helpdesk/desk");
const VITE_CONFIG = path.resolve(__dirname, "vite.config.cjs");

if (!fs.existsSync(path.join(HELPDESK_DESK, "node_modules"))) {
	execSync("yarn install", { cwd: HELPDESK_DESK, stdio: "inherit" });
}

execSync(`yarn vite --config "${VITE_CONFIG}"`, {
	cwd: HELPDESK_DESK,
	stdio: "inherit",
});
