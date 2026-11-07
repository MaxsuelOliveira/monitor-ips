const { spawn } = require("node:child_process");
const readline = require("node:readline");
const path = require("node:path");

class PythonClient {
  constructor({
    root,
    demo = false,
    backups,
    python = process.env.MONITOR_PYTHON || "python",
  }) {
    this.sequence = 0;
    this.pending = new Map();
    this.stderr = "";
    const args = ["-u", "-m", "monitor_tool.bridge"];
    if (demo) args.push("--demo");
    if (backups) args.push("--backup-dir", path.resolve(backups));
    this.child = spawn(python, args, {
      cwd: root,
      windowsHide: true,
      shell: false,
      env: { ...process.env, PYTHONUTF8: "1", PYTHONIOENCODING: "utf-8" },
      stdio: ["pipe", "pipe", "pipe"],
    });
    readline
      .createInterface({ input: this.child.stdout })
      .on("line", (line) => {
        try {
          const reply = JSON.parse(line);
          const pending = this.pending.get(reply.id);
          if (!pending) return;
          this.pending.delete(reply.id);
          reply.error
            ? pending.reject(new Error(reply.error))
            : pending.resolve(reply.result);
        } catch {
          this.fail(new Error("Resposta inválida do backend Python."));
        }
      });
    this.child.stderr.on("data", (data) => {
      this.stderr = (this.stderr + data.toString()).slice(-8000);
    });
    this.child.on("error", (error) =>
      this.fail(new Error(`Não foi possível iniciar Python: ${error.message}`)),
    );
    this.child.on("exit", (code) => {
      this.exited = true;
      this.fail(new Error(`Backend Python encerrou (${code}). ${this.stderr}`));
    });
    this.child.stdin.on("error", (error) => this.fail(error));
  }
  get busy() {
    return this.pending.size > 0;
  }
  fail(error) {
    for (const task of this.pending.values()) task.reject(error);
    this.pending.clear();
  }
  request(method, params = {}) {
    if (this.exited || this.child.killed)
      return Promise.reject(
        new Error("Backend indisponível. Reabra o aplicativo."),
      );
    const id = ++this.sequence;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.child.stdin.write(JSON.stringify({ id, method, params }) + "\n");
    });
  }
  async close() {
    if (this.exited) return;
    if (this.busy) throw new Error("Aguarde a operação terminar.");
    const closed = new Promise((resolve) => this.child.once("exit", resolve));
    this.child.stdin.end();
    const timer = setTimeout(() => {
      if (!this.exited) this.child.kill();
    }, 5000);
    await closed;
    clearTimeout(timer);
  }
}

module.exports = { PythonClient };
