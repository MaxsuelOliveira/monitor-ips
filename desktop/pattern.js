for (const [id, values] of Object.entries({
  shadows: [0, 1, 2, 4, 8, 12, 16, 24, 32],
  highlights: [224, 232, 240, 244, 248, 252, 254, 255],
})) {
  for (const value of values) {
    const cell = document.createElement("div");
    cell.className = "swatch";
    const color = document.createElement("div");
    color.className = "color";
    color.style.backgroundColor = `rgb(${value},${value},${value})`;
    const label = document.createElement("div");
    label.className = "caption";
    label.textContent = value;
    cell.append(color, label);
    document.getElementById(id).append(cell);
  }
}
for (let value = 0; value < 256; value++) {
  const cell = document.createElement("span");
  cell.style.backgroundColor = `rgb(${value},${value},${value})`;
  document.getElementById("grayscale").append(cell);
}
document
  .getElementById("close")
  .addEventListener("click", () => window.close());
const parameters = new URLSearchParams(location.search);
document.getElementById("pattern-label").textContent =
  parameters.get("label") || "Padrão de teste";
const blackMode = parameters.get("mode") === "black";
if (blackMode) {
  document.getElementById("black-reset").addEventListener("click", () => {
    window.monitor.patternStep({ reset: true });
  });
  document.documentElement.style.backgroundColor = "#000";
  document.body.classList.add("black-mode");
  document.getElementById("black-test").hidden = false;
  document.getElementById("pattern-title").textContent = "Teste de preto";
  window.monitor.onPatternValue((value) => {
    if (![0, 8, 16, 32].includes(value)) return;
    document.body.style.backgroundColor = `rgb(${value},${value},${value})`;
    document.documentElement.style.backgroundColor = `rgb(${value},${value},${value})`;
    document.getElementById("black-value").textContent =
      `Nível digital ${value} / 255`;
  });
}
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") window.close();
  if (event.code === "Space" && blackMode) {
    event.preventDefault();
    window.monitor.patternStep();
  }
});
