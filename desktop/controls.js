/* Controles acessíveis com aparência própria; nenhuma escrita de hardware aqui. */
(() => {
  const node = (tag, cls, text) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = text;
    return el;
  };
  const selects = [];
  function customSelect(select) {
    const wrapper = node("div", "custom-select");
    const button = node("button", "select-trigger");
    button.type = "button";
    button.id = select.id + "-trigger";
    button.setAttribute("role", "combobox");
    button.setAttribute("aria-haspopup", "listbox");
    button.setAttribute("aria-expanded", "false");
    const list = node("div", "select-menu");
    list.id = select.id + "-options";
    list.setAttribute("role", "listbox");
    list.hidden = true;
    button.setAttribute("aria-controls", list.id);
    const label = document.querySelector(`label[for="${select.id}"]`);
    if (label) {
      label.id ||= select.id + "-label";
      button.setAttribute("aria-labelledby", label.id);
      label.addEventListener("click", (event) => {
        event.preventDefault();
        button.focus();
      });
    }
    select.before(wrapper);
    wrapper.append(button, list, select);
    select.hidden = true;
    let active = 0;
    const close = () => {
      list.hidden = true;
      button.setAttribute("aria-expanded", "false");
      button.removeAttribute("aria-activedescendant");
    };
    function choose(index) {
      if (
        select.disabled ||
        !select.options[index] ||
        select.options[index].disabled
      )
        return;
      select.selectedIndex = index;
      close();
      sync();
      select.dispatchEvent(new Event("change", { bubbles: true }));
      button.focus();
    }
    function mark(index) {
      active = Math.max(0, Math.min(select.options.length - 1, index));
      [...list.children].forEach((item, i) =>
        item.classList.toggle("highlighted", i === active),
      );
      if (list.children[active]) {
        button.setAttribute("aria-activedescendant", list.children[active].id);
        list.children[active].scrollIntoView({ block: "nearest" });
      }
    }
    function sync() {
      const text = select.selectedOptions[0]?.textContent || "Selecione";
      if (button.textContent !== text) button.textContent = text;
      button.disabled = select.disabled;
      button.dataset.locked = String(select.disabled);
      list.replaceChildren();
      [...select.options].forEach((option, i) => {
        const item = node("div", "select-option", option.textContent);
        item.id = select.id + "-option-" + i;
        item.setAttribute("role", "option");
        item.setAttribute("aria-selected", String(option.selected));
        item.setAttribute("aria-disabled", String(option.disabled));
        item.addEventListener("mousedown", (event) => event.preventDefault());
        item.addEventListener("click", () => choose(i));
        list.append(item);
      });
      if (select.disabled) close();
    }
    button.addEventListener("click", () => {
      if (list.hidden) {
        for (const other of selects) other.close();
        list.hidden = false;
        button.setAttribute("aria-expanded", "true");
        mark(select.selectedIndex);
      } else close();
    });
    button.addEventListener("keydown", (event) => {
      if (
        [
          "ArrowDown",
          "ArrowUp",
          "Home",
          "End",
          "Enter",
          " ",
          "Escape",
        ].includes(event.key)
      )
        event.preventDefault();
      if (event.key === "Escape") close();
      else if (event.key === "Enter" || event.key === " ") {
        if (!list.hidden) choose(active);
        else button.click();
      } else if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        if (list.hidden) {
          list.hidden = false;
          button.setAttribute("aria-expanded", "true");
          active = select.selectedIndex;
        }
        mark(
          event.key === "Home"
            ? 0
            : event.key === "End"
              ? select.options.length - 1
              : active + (event.key === "ArrowDown" ? 1 : -1),
        );
      } else if (event.key === "Tab") close();
    });
    select.addEventListener("change", sync);
    new MutationObserver(sync).observe(select, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ["disabled", "selected"],
    });
    document.addEventListener("pointerdown", (event) => {
      if (!wrapper.contains(event.target)) close();
    });
    document.addEventListener("focusin", (event) => {
      if (!wrapper.contains(event.target)) close();
    });
    selects.push({ sync, close });
    sync();
  }
  function createControl({
    name,
    label,
    min = 0,
    max,
    step = 1,
    value,
    disabled = false,
    description = "",
    compact = false,
  }) {
    const card = node("div", "control-card " + (compact ? "compact" : ""));
    card.dataset.control = name;
    const title = node("label", "control-label", label);
    title.htmlFor = "value-" + name;
    const heading = node("div", "control-heading");
    const number = node("input", "value-input");
    number.id = title.htmlFor;
    number.name = name;
    number.type = "text";
    number.inputMode = step < 1 ? "decimal" : "numeric";
    number.dataset.value = "true";
    number.dataset.step = String(step);
    number.dataset.min = String(min);
    number.dataset.max = String(max);
    number.dataset.locked = String(disabled);
    number.disabled = disabled;
    number.setAttribute("role", "spinbutton");
    number.setAttribute("aria-valuemin", min);
    number.setAttribute("aria-valuemax", max);
    number.setAttribute("aria-label", label);
    const numeric = node("div", "number-control");
    const minus = node("button", "step-button", "−"),
      plus = node("button", "step-button", "+");
    for (const [button, action] of [
      [minus, "Diminuir"],
      [plus, "Aumentar"],
    ]) {
      button.type = "button";
      button.dataset.locked = String(disabled);
      button.disabled = disabled;
      button.setAttribute("aria-label", action + " " + label.toLowerCase());
    }
    numeric.append(minus, number, plus);
    heading.append(title, numeric);
    const sliderWrap = node("div", "slider-wrap");
    const track = node("div", "slider-track"),
      fill = node("span", "slider-fill");
    track.append(fill);
    const range = node("input", "custom-range");
    range.type = "range";
    range.min = min;
    range.max = max;
    range.step = step;
    range.disabled = disabled;
    range.dataset.locked = String(disabled);
    range.setAttribute(
      "aria-label",
      "Controle deslizante de " + label.toLowerCase(),
    );
    sliderWrap.append(track, range);
    const error = node("span", "control-error");
    error.id = name + "-error";
    error.hidden = true;
    number.setAttribute("aria-describedby", error.id);
    const limits = node("div", "control-limits");
    limits.append(node("span", "", min), node("span", "", max));
    const format = (val) =>
      step < 1
        ? Number(val).toFixed(step === 0.01 ? 2 : 1)
        : String(Math.round(val));
    function refresh(val) {
      const percent = ((Number(val) - min) / (max - min || 1)) * 100;
      fill.style.width = Math.max(0, Math.min(100, percent)) + "%";
      range.value = val;
      number.setAttribute("aria-valuenow", val);
    }
    function change(val) {
      const rounded = Math.round(val / step) * step;
      number.value = format(Math.max(min, Math.min(max, rounded)));
      refresh(number.value);
      number.setAttribute("aria-invalid", "false");
      error.hidden = true;
      number.dispatchEvent(new Event("input", { bubbles: true }));
    }
    range.addEventListener("input", () => change(Number(range.value)));
    const currentNumber = () => {
      const parsed = Number(number.value.replace(",", "."));
      return number.value.trim() && Number.isFinite(parsed) ? parsed : value;
    };
    minus.addEventListener("click", () => change(currentNumber() - step));
    plus.addEventListener("click", () => change(currentNumber() + step));
    number.addEventListener("keydown", (event) => {
      if (event.key === "ArrowUp" || event.key === "ArrowDown") {
        event.preventDefault();
        change(
          currentNumber() +
            (event.key === "ArrowUp" ? step : -step),
        );
      }
    });
    number.addEventListener("input", () => {
      const raw = number.value.trim().replace(",", ".");
      const valid =
        /^\d+(\.\d+)?$/.test(raw) &&
        Number(raw) >= min &&
        Number(raw) <= max &&
        (step < 1 || Number.isInteger(Number(raw)));
      number.setAttribute("aria-invalid", String(Boolean(raw) && !valid));
      error.hidden = !raw || valid;
      error.textContent = `Use um valor de ${min} a ${max}.`;
      if (valid) refresh(Number(raw));
    });
    number.value = disabled ? "" : format(value);
    refresh(disabled ? min : value);
    card.append(
      heading,
      node("p", "control-description", description),
      sliderWrap,
      limits,
      error,
    );
    return card;
  }
  window.ControlInputs = {
    create: createControl,
    sync: () => selects.forEach((select) => select.sync()),
  };
  document.querySelectorAll("select").forEach(customSelect);
})();
