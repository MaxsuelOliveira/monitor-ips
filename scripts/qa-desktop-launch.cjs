// Instância própria: demo ou hardware somente leitura. Fechar por window.monitor.qa('quit').
const { spawn } = require("node:child_process");
const fs = require("node:fs/promises");
const net = require("node:net");
const path = require("node:path");
const crypto = require("node:crypto");
(async () => {
  const root = path.resolve(__dirname, "..");
  const server = net.createServer();
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  await new Promise((resolve) => server.close(resolve));
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const mode = process.argv.includes("--real-read-only")
    ? "--read-only"
    : "--demo";
  const child = spawn(
    require("electron"),
    [
      root,
      mode,
      "--qa",
      `--remote-debugging-port=${port}`,
      "--remote-debugging-address=127.0.0.1",
    ],
    { cwd: root, env, windowsHide: true, stdio: "inherit" },
  );
  const metadata = {
    port,
    pid: child.pid,
    session: "monitor-match-" + crypto.randomBytes(5).toString("hex"),
    command: `electron . ${mode} --qa`,
    owner: "scripts/qa-desktop-launch.cjs",
  };
  await fs.mkdir(path.join(root, "output"), { recursive: true });
  await fs.writeFile(
    path.join(root, "output", "desktop-qa.json"),
    JSON.stringify(metadata, null, 2),
  );
  console.log(JSON.stringify(metadata));
  child.on("error", (error) => {
    console.error(error);
    process.exitCode = 1;
  });
  child.on("exit", (code) => {
    console.log("Owned Electron exited:", code);
    process.exitCode = code || 0;
  });
})();
