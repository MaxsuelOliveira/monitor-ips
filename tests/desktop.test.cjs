const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { PythonClient } = require("../desktop/python-client.cjs");

test("Electron client → Python RPC: compare, apply, restore and close owned child", async () => {
  const backups = await fs.mkdtemp(path.join(os.tmpdir(), "monitor-ips-rpc-"));
  const client = new PythonClient({
    root: path.resolve(__dirname, ".."),
    demo: true,
    backups,
  });
  try {
    const before = await client.request("state");
    assert.equal(before.demo, true);
    const preview = await client.request("preview_match", {
      source: "demo-ips",
      target: "demo-va",
    });
    assert.equal(
      preview.changes.find((c) => c.feature === "brightness").after,
      35,
    );
    const result = await client.request("apply", { token: preview.token });
    assert.equal(result.ok, true);
    const after = await client.request("state");
    assert.equal(after.monitors[1].values.brightness.current, 35);
    const restore = await client.request("preview_restore", {
      target: "demo-va",
      path: result.backup,
    });
    assert.equal(
      (await client.request("apply", { token: restore.token })).ok,
      true,
    );
    assert.equal(
      (await client.request("state")).monitors[1].values.brightness.current,
      140,
    );
    await assert.rejects(
      client.request("apply", { token: preview.token }),
      /expirada/,
    );
  } finally {
    await client.close();
    assert.equal(client.exited, true);
    await fs.rm(backups, { recursive: true, force: true });
  }
});
