/**
 * Vite config for MCX Helpdesk UI overrides.
 * Stages overrides under helpdesk/desk/.mcx-ui-staging/ so module resolution stays in-tree.
 */
const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

const HELPDESK_DESK = path.resolve(__dirname, "../../helpdesk/desk");
const HELPDESK_SRC = path.join(HELPDESK_DESK, "src");
const OVERRIDES_DIR = path.resolve(__dirname, "overrides");
const STAGING_DIR = path.join(HELPDESK_DESK, ".mcx-ui-staging");
const MCX_TAILWIND_CONFIG = path.join(HELPDESK_DESK, "tailwind.mcx.config.js");
const requireHelpdesk = createRequire(path.join(HELPDESK_DESK, "package.json"));
const { loadConfigFromFile } = requireHelpdesk("vite");

const CODE_EXTENSIONS = new Set([".vue", ".ts", ".js", ".tsx", ".jsx"]);

function walkOverrideFiles(dir, base = dir) {
	const entries = [];
	for (const name of fs.readdirSync(dir)) {
		const full = path.join(dir, name);
		if (fs.statSync(full).isDirectory()) {
			entries.push(...walkOverrideFiles(full, base));
			continue;
		}
		if (!CODE_EXTENSIONS.has(path.extname(name))) continue;
		entries.push(path.relative(base, full).split(path.sep).join("/"));
	}
	return entries;
}

function stageOverrides() {
	fs.rmSync(STAGING_DIR, { recursive: true, force: true });
	for (const rel of walkOverrideFiles(OVERRIDES_DIR)) {
		const src = path.join(OVERRIDES_DIR, rel);
		const dest = path.join(STAGING_DIR, rel);
		fs.mkdirSync(path.dirname(dest), { recursive: true });
		fs.copyFileSync(src, dest);
	}
}

function writeMcxTailwindConfig() {
	// Tailwind must scan staged MCX overrides or utility classes are missing from CSS.
	const content = `import base from "./tailwind.config.js";

export default {
	...base,
	content: [
		...(base.content || []),
		"./.mcx-ui-staging/**/*.{vue,js,ts,jsx,tsx}",
	],
};
`;
	fs.writeFileSync(MCX_TAILWIND_CONFIG, content);
}

function buildOverrideAliases() {
	const aliases = [];
	const appOverride = path.join(STAGING_DIR, "App.vue");
	if (fs.existsSync(appOverride)) {
		aliases.push({ find: path.join(HELPDESK_SRC, "App.vue"), replacement: appOverride });
	}
	for (const rel of walkOverrideFiles(OVERRIDES_DIR)) {
		const stagingPath = path.join(STAGING_DIR, rel);
		aliases.push({ find: `@/${rel}`, replacement: stagingPath });
		const withoutExt = rel.replace(/\.(vue|ts|js|tsx|jsx)$/, "");
		if (withoutExt !== rel) {
			aliases.push({ find: `@/${withoutExt}`, replacement: stagingPath });
		}
		if (rel === "router/index.ts") {
			aliases.push({ find: "@/router", replacement: stagingPath });
		}
	}
	return aliases;
}

function normalizeAliases(alias) {
	if (!alias) return [];
	if (Array.isArray(alias)) return [...alias];
	return Object.entries(alias).map(([find, replacement]) => ({ find, replacement }));
}

module.exports = async (env) => {
	stageOverrides();
	writeMcxTailwindConfig();

	const loaded = await loadConfigFromFile(
		env,
		path.join(HELPDESK_DESK, "vite.config.js"),
		HELPDESK_DESK
	);

	if (!loaded) {
		throw new Error("Failed to load Helpdesk vite.config.js");
	}

	const config = loaded.config;
	const helpdeskAliases = normalizeAliases(config.resolve?.alias).filter(
		(entry) => entry.find !== "tailwind.config.js"
	);

	config.resolve = {
		...config.resolve,
		alias: [
			...buildOverrideAliases(),
			{ find: "tailwind.config.js", replacement: MCX_TAILWIND_CONFIG },
			...helpdeskAliases,
		],
	};

	config.plugins = [
		...(config.plugins || []),
		{
			name: "mcx-resolve-app-entry",
			enforce: "pre",
			resolveId(source, importer) {
				if (
					source === "./App.vue" &&
					importer &&
					importer.replace(/\\/g, "/").includes("/desk/src/main.js")
				) {
					const override = path.join(STAGING_DIR, "App.vue");
					if (fs.existsSync(override)) return override;
				}
				return null;
			},
		},
	];

	return config;
};
