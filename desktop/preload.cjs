const { contextBridge, ipcRenderer } = require("electron");
const invoke = (name) => (params) =>
  ipcRenderer.invoke("monitor:" + name, params);
contextBridge.exposeInMainWorld("monitor", {
  state: invoke("state"),
  previewMatch: invoke("preview_match"),
  previewSet: invoke("preview_set"),
  apply: invoke("apply"),
  discard: invoke("discard"),
  backup: invoke("backup"),
  restore: invoke("restore"),
  openBackups: invoke("backups"),
  pattern: invoke("pattern"),
  qa: invoke("qa"),
});
