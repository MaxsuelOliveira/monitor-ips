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
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") window.close();
});
