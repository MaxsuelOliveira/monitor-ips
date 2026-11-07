const { contextBridge, ipcRenderer } = require("electron");
const invoke = (name) => (params) =>
  ipcRenderer.invoke("monitor:" + name, params);
contextBridge.exposeInMainWorld("monitor", {
  state: invoke("state"),
  previewMatch: invoke("preview_match"),
  previewSet: invoke("preview_set"),
  previewVisual: invoke("preview_visual"),
  previewUndo: invoke("preview_undo"),
  diagnostics: invoke("diagnostics"),
  apply: invoke("apply"),
  discard: invoke("discard"),
  backup: invoke("backup"),
  restore: invoke("restore"),
  openBackups: invoke("backups"),
  pattern: invoke("pattern"),
  displaySettings: invoke("display_settings"),
  patternStep: invoke("pattern_step"),
  onPatternValue: (callback) => {
    const listener = (_event, value) => callback(value);
    ipcRenderer.on("pattern:value", listener);
    return () => ipcRenderer.removeListener("pattern:value", listener);
  },
  qa: invoke("qa"),
});
