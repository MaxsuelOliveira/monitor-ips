const {
  app,
  BrowserWindow,
  ipcMain,
  dialog,
  protocol,
  net,
  screen,
  shell,
} = require("electron");
const path = require("node:path");
const fs = require("node:fs/promises");
const { pathToFileURL } = require("node:url");
const { PythonClient } = require("./python-client.cjs");

protocol.registerSchemesAsPrivileged([
  {
    scheme: "monitor",
    privileges: { standard: true, secure: true, supportFetchAPI: true },
  },
]);
const root = path.resolve(__dirname, "..");
const demo = process.argv.includes("--demo");
const readOnly = process.argv.includes("--read-only");
const qa = (demo || readOnly) && process.argv.includes("--qa");
if (qa)
  app.setPath(
    "userData",
    path.join(root, "output", `desktop-qa-userdata-${process.pid}`),
  );
const backupIndex = process.argv.indexOf("--backup-dir");
let mainWindow,
  client,
  quitting = false,
  active = false;
const patternWindows = new Set();
let patternLevel = 0;

async function handle(method, params) {
  if (readOnly && method === "apply")
    throw new Error(
      "Instância de diagnóstico somente leitura. Nenhum ajuste será aplicado.",
    );
  if (active) throw new Error("Outra operação está em andamento.");
  active = true;
  try {
    return await client.request(method, params);
  } finally {
    active = false;
  }
}

function secureWindow(options) {
  const win = new BrowserWindow({
    ...options,
    backgroundColor: "#171719",
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.cjs"),
      ...options.webPreferences,
    },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (event) => event.preventDefault());
  win.webContents.session.setPermissionRequestHandler(
    (_wc, _permission, callback) => callback(false),
  );
  return win;
}

app
  .whenReady()
  .then(async () => {
    protocol.handle("monitor", async (request) => {
      const url = new URL(request.url);
      const relative =
        decodeURIComponent(url.pathname).replace(/^\/+/, "") || "index.html";
      const base = relative.startsWith("fonts/")
        ? path.join(root, "node_modules", "@fontsource")
        : __dirname;
      const resource = relative.startsWith("fonts/")
        ? relative.slice(6)
        : relative;
      const target = path.resolve(base, resource);
      if (url.host !== "app" || !target.startsWith(base + path.sep))
        return new Response("Forbidden", { status: 403 });
      const response = await net.fetch(pathToFileURL(target).toString());
      const headers = new Headers(response.headers);
      headers.set("Cache-Control", "no-store");
      return new Response(response.body, { status: response.status, headers });
    });
    client = new PythonClient({
      root,
      demo,
      backups:
        backupIndex >= 0
          ? process.argv[backupIndex + 1]
          : qa && demo
            ? path.join(root, "output", "desktop-qa-backups")
            : undefined,
    });
    const area = screen.getPrimaryDisplay().workAreaSize;
    mainWindow = secureWindow({
      width: Math.min(1180, area.width),
      height: Math.min(900, area.height),
      minWidth: Math.min(820, area.width),
      minHeight: Math.min(640, area.height),
      title: "Monitor IPS",
    });
    const allowed = (event) => {
      if (
        event.sender !== mainWindow.webContents ||
        event.senderFrame?.url !== "monitor://app/index.html"
      ) {
        throw new Error("Origem IPC não permitida.");
      }
    };
    for (const method of [
      "state",
      "preview_match",
      "preview_set",
      "preview_visual",
      "preview_undo",
      "diagnostics",
      "apply",
      "discard",
    ]) {
      ipcMain.handle("monitor:" + method, async (event, params = {}) => {
        allowed(event);
        return handle(method, params);
      });
    }
    ipcMain.handle("monitor:backup", async (event, params) => {
      allowed(event);
      return handle("backup", { target: params.target });
    });
    ipcMain.handle("monitor:restore", async (event, params) => {
      allowed(event);
      if (active) throw new Error("Aguarde a operação atual.");
      const selection =
        qa && params.qaPath
          ? { canceled: false, filePaths: [params.qaPath] }
          : await dialog.showOpenDialog(mainWindow, {
              title: "Restaurar backup do destino",
              filters: [{ name: "Backup Monitor IPS", extensions: ["json"] }],
              properties: ["openFile"],
            });
      if (selection.canceled) return null;
      return handle("preview_restore", {
        target: params.target,
        path: selection.filePaths[0],
      });
    });
    ipcMain.handle("monitor:backups", async (event) => {
      allowed(event);
      const state = await handle("state", {});
      await fs.mkdir(state.backup_dir, { recursive: true });
      const error = await shell.openPath(state.backup_dir);
      if (error) throw new Error(error);
    });
    ipcMain.handle("monitor:display_settings", async (event) => {
      allowed(event);
      if (!qa) await shell.openExternal("ms-settings:display");
      return true;
    });
    ipcMain.handle("monitor:pattern_step", async (event, params) => {
      const sender = BrowserWindow.fromWebContents(event.sender);
      if (!patternWindows.has(sender))
        throw new Error("Janela de teste não autorizada.");
      patternLevel = params?.reset === true ? 0 : (patternLevel + 1) % 4;
      for (const win of patternWindows)
        if (!win.isDestroyed())
          win.webContents.send("pattern:value", [0, 8, 16, 32][patternLevel]);
      return true;
    });
    ipcMain.handle("monitor:pattern", async (event, params) => {
      allowed(event);
      const state = await handle("state", {});
      const ids = params.pair
        ? [params.source, params.target]
        : [params.target];
      if (new Set(ids).size !== ids.length)
        throw new Error("Escolha duas telas diferentes.");
      const monitors = ids.map(
        (id) => state.monitors.find((p) => p.monitor.id === id)?.monitor,
      );
      if (monitors.some((m) => !m))
        throw new Error("Monitor ausente. Atualize a lista.");
      for (const win of patternWindows) if (!win.isDestroyed()) win.close();
      patternLevel = 0;
      const opened = [];
      try {
        for (const monitor of monitors) {
          const bounds = monitor.bounds;
          const point = bounds
            ? screen.screenToDipPoint({
                x: Math.round((bounds[0] + bounds[2]) / 2),
                y: Math.round((bounds[1] + bounds[3]) / 2),
              })
            : { x: 60, y: 60 };
          const display = screen.getDisplayNearestPoint(point);
          const pattern = secureWindow({
            ...display.bounds,
            width: qa && !params.fullscreen ? 900 : display.bounds.width,
            height: qa && !params.fullscreen ? 680 : display.bounds.height,
            title: "Teste visual",
            frame: qa && !params.fullscreen,
            show: false,
          });
          patternWindows.add(pattern);
          opened.push(pattern);
          pattern.on("closed", () => patternWindows.delete(pattern));
          const mode = params.mode === "black" ? "black" : "steps";
          const label = `${monitor.device.replace(/^.*DISPLAY/i, "DISPLAY ")} · ${monitor.name}`;
          await pattern.loadURL(
            "monitor://app/pattern.html?" +
              new URLSearchParams({ mode, label }),
          );
          pattern.setBounds(display.bounds);
          if (qa && !params.fullscreen) pattern.setSize(900, 680);
          pattern.show();
          if (!qa || params.fullscreen) pattern.setFullScreen(true);
          pattern.webContents.send(
            "pattern:value",
            [0, 8, 16, 32][patternLevel],
          );
        }
      } catch (error) {
        for (const win of opened) if (!win.isDestroyed()) win.close();
        throw error;
      }
      return true;
    });
    // Canal de QA apenas em DEMO ou diagnóstico com apply bloqueado no main.
    if (qa)
      ipcMain.handle("monitor:qa", async (event, action) => {
        allowed(event);
        if (action === "screenshot") {
          await fs.mkdir(path.join(root, "output"), { recursive: true });
          await fs.writeFile(
            path.join(root, "output", "electron-demo.png"),
            (await mainWindow.webContents.capturePage()).toPNG(),
          );
          return true;
        }
        if (action === "quit") {
          mainWindow.close();
          return true;
        }
        if (action === "displays")
          return {
            displays: screen.getAllDisplays().map((display) => ({
              id: display.id,
              bounds: display.bounds,
              physical: screen.dipToScreenRect(null, display.bounds),
            })),
            patterns: [...patternWindows].map((win) => ({
              bounds: win.getBounds(),
              url: win.webContents.getURL(),
            })),
          };
        if (action?.resize) {
          mainWindow.setSize(...action.resize);
          return true;
        }
        throw new Error("Ação QA não permitida.");
      });
    mainWindow.on("close", (event) => {
      if (quitting) return;
      event.preventDefault();
      if (active || client.busy) {
        dialog.showMessageBox(mainWindow, {
          type: "info",
          message: "Aguarde a operação terminar antes de fechar.",
        });
        return;
      }
      quitting = true;
      client.close().finally(() => app.quit());
    });
    await mainWindow.loadURL("monitor://app/index.html");
  })
  .catch((error) => {
    dialog.showErrorBox("Monitor IPS", error.message);
    app.quit();
  });

app.on("window-all-closed", () => {
  if (!quitting) app.quit();
});
app.on("before-quit", (event) => {
  if (client && !quitting) {
    event.preventDefault();
    mainWindow?.close();
  }
});
