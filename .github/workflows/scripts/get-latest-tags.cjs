const fs = require("fs");
const path = require("path");

async function tagExists(repo, tag) {
  const tokenRes = await fetch(
    `https://ghcr.io/token?scope=repository:${repo}:pull`,
  );
  const { token } = await tokenRes.json();

  const res = await fetch(`https://ghcr.io/v2/${repo}/manifests/${tag}`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.oci.image.index.v1+json",
    },
  });

  const data = await res.json();

  if (data.errors) {
    if (
      data.errors[0].code === "MANIFEST_UNKNOWN" ||
      data.errors[0].code === "DENIED"
    ) {
      return false;
    } else {
      throw new Error(JSON.stringify(data, null, 2));
    }
  } else {
    return true;
  }
}

async function main() {
  const dirs = fs
    .readdirSync(".")
    .filter((f) => fs.statSync(f).isDirectory() && !f.startsWith("."));

  const missing = [];

  for (const dir of dirs) {
    const configPath = path.join(dir, "config.yaml");
    if (!fs.existsSync(configPath)) continue;

    const content = fs.readFileSync(configPath, "utf-8");
    const match = content.match(/^version:\s*["']?([^"'\n]+)["']?/m);
    if (!match) throw new Error(`Failed to parse version from ${configPath}`);

    const version = match[1].trim();
    const image = `ghcr.io/easrng/ha-addon-${dir}`;

    if (!(await tagExists(`easrng/ha-addon-${dir}`, version))) {
      missing.push({ dir, version, image });
    }
  }

  console.log(`addons=${JSON.stringify(missing)}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
