import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "../..");
loadEnvFile(resolve(repoRoot, ".env"));
const defaultEmulateCli = resolve(repoRoot, "../emulate/packages/emulate/dist/index.js");
const sharedPlugins = requireEnv("EMULATE_PLUGINS_DIR");
const args = parseArgs(process.argv.slice(2));

const port = args.port ?? process.env.KUBERNETES_EMULATOR_PORT ?? "4100";
const emulateCli = resolve(args.emulateCli ?? process.env.EMULATE_CLI ?? defaultEmulateCli);
const plugin = resolve(args.plugin ?? process.env.KUBERNETES_EMULATOR_PLUGIN ?? resolve(sharedPlugins, "@kubernetes/api-emulator/index.mjs"));
const seed = resolve(args.seed ?? process.env.KUBERNETES_EMULATOR_SEED ?? resolve(here, "kubernetes-crashloop.json"));
const command = [
  emulateCli,
  "start",
  "--service",
  "kubernetes",
  "--plugin",
  plugin,
  "--seed",
  seed,
  "--port",
  port,
];

if (args.printCommand) {
  console.log(JSON.stringify({ executable: "node", args: command, url: `http://localhost:${port}` }));
  process.exit(0);
}

for (const [label, path] of [
  ["emulate CLI", emulateCli],
  ["Kubernetes plugin", plugin],
  ["Kubernetes seed", seed],
]) {
  if (!existsSync(path)) {
    console.error(`${label} not found: ${path}`);
    process.exit(1);
  }
}

console.log(`Starting Kubernetes emulator on http://localhost:${port}`);
const child = spawn("node", command, {
  cwd: repoRoot,
  stdio: "inherit",
  env: { ...process.env, NO_COLOR: process.env.NO_COLOR ?? "1" },
});

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 0);
});

function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--print-command") parsed.printCommand = true;
    else if (arg === "--port") parsed.port = argv[++index];
    else if (arg === "--emulate-cli") parsed.emulateCli = argv[++index];
    else if (arg === "--plugin") parsed.plugin = argv[++index];
    else if (arg === "--seed") parsed.seed = argv[++index];
    else {
      console.error(`Unknown option: ${arg}`);
      process.exit(1);
    }
  }
  return parsed;
}

function loadEnvFile(path) {
  if (!existsSync(path)) return;
  const content = readFileSync(path, "utf8");
  for (const line of content.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx < 0) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    if (process.env[key]) continue;
    process.env[key] = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
  }
}

function requireEnv(key) {
  const value = process.env[key]?.trim();
  if (!value) {
    console.error(`Missing ${key}. Set it in your shell or ${resolve(repoRoot, ".env")}.`);
    process.exit(1);
  }
  return value;
}
