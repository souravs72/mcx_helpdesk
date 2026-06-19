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
const DESK_ASSETS = path.resolve(__dirname, "../../helpdesk/helpdesk/public/desk/assets");

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
	verifyDeskBuild();
	console.log("MCX Helpdesk desk build complete.");
} finally {
	fs.rmSync(STAGING_DIR, { recursive: true, force: true });
	const mcTailwind = path.join(HELPDESK_DESK, "tailwind.mcx.config.js");
	if (fs.existsSync(mcTailwind)) fs.rmSync(mcTailwind);
}

function verifyDeskBuild() {
	const assets = fs.readdirSync(DESK_ASSETS);
	const chatbotBundle = assets.find(
		(name) =>
			name.endsWith(".js") &&
			!name.endsWith(".map") &&
			fs.readFileSync(path.join(DESK_ASSETS, name), "utf8").includes("FAQ Assistant")
	);
	if (!chatbotBundle) {
		throw new Error("MCX desk build verification failed: FAQ Assistant UI not found in desk assets.");
	}
	const cssFile = assets.find((name) => name.startsWith("index-") && name.endsWith(".css"));
	if (cssFile) {
		const css = fs.readFileSync(path.join(DESK_ASSETS, cssFile), "utf8");
		if (!css.includes("bg-violet-500")) {
			throw new Error("MCX desk build verification failed: chatbot Tailwind styles missing from CSS.");
		}
	}
	console.log(`Verified MCX desk build (${chatbotBundle}).`);
}
