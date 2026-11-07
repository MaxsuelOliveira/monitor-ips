/* Expansores compartilhados: botão nativo para clique, Enter e Espaço. */
document.querySelectorAll(".disclosure-trigger").forEach((trigger) => {
  const panel = document.getElementById(trigger.getAttribute("aria-controls"));
  const action = trigger.querySelector(".disclosure-action");
  const list = panel.querySelector("[data-disclosure-list]");
  const empty = panel.querySelector("[data-disclosure-empty]");
  if (list && empty) {
    const updateEmpty = () => { empty.hidden = list.children.length > 0; };
    updateEmpty();
    new MutationObserver(updateEmpty).observe(list, { childList: true });
  }
  trigger.addEventListener("click", () => {
    const expanded = trigger.getAttribute("aria-expanded") !== "true";
    trigger.setAttribute("aria-expanded", String(expanded));
    panel.hidden = !expanded;
    action.textContent = expanded ? "Ocultar" : "Mostrar";
  });
});
