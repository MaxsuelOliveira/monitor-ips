/* O renderer não acessa Node, arquivos, comandos nem a API Win32. */
const api = window.monitor;
const byId = (id) => document.getElementById(id);
const features = {
  brightness: "Brilho",
  contrast: "Contraste",
  red: "Ganho vermelho",
  green: "Ganho verde",
  blue: "Ganho azul",
};
const labels = {
  ...features,
  color_preset: "Modo de cor",
  tone_curve: "Curva SDR",
};
let state,
  plan,
  busy = false,
  previewKind = "match",
  historyCount = 0;

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function selected(which) {
  return state?.monitors.find((p) => p.monitor.id === byId(which).value);
}
function role(profile) {
  return state?.roles[profile?.monitor.id]?.toUpperCase() || "Tela";
}
function displayName(profile) {
  return profile?.monitor.device.replace(/^.*DISPLAY/i, "DISPLAY ") || "—";
}
function modelName(profile) {
  return (
    profile?.monitor.name.match(/\(([^)]+)\)$/)?.[1] ||
    profile?.monitor.name ||
    "Indisponível"
  );
}
function colorName(value) {
  return (
    { 5: "Preset 05", 8: "Preset 08", 11: "Usuário 1", 12: "Usuário 2" }[
      value
    ] || (value ? "0x" + value.toString(16).toUpperCase() : "—")
  );
}
function log(text) {
  const time = new Date().toLocaleTimeString("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  });
  byId("history-list").prepend(element("li", `${time} · ${text}`));
  byId("history-count").textContent = String(++historyCount);
}
function notice(text, error = false) {
  byId("notice").textContent = text;
  byId("notice").classList.toggle("error", error);
  byId("notice").hidden = !text;
}
function lock() {
  const profile = selected("target");
  for (const id of ["backup", "restore", "pattern"])
    byId(id).dataset.locked = String(!profile);
  byId("compare-pattern").dataset.locked = String(
    !profile ||
      !selected("source") ||
      byId("source").value === byId("target").value,
  );
  byId("undo").dataset.locked = String(!profile?.can_undo);
  byId("manual-tone").dataset.locked = String(!profile?.tone_available);
  document
    .querySelectorAll("#tone-fields button, #tone-fields input")
    .forEach((node) => {
      node.dataset.locked = String(
        !byId("manual-tone").checked || !profile?.tone_available,
      );
    });
  document.querySelectorAll("button, select, input").forEach((node) => {
    node.disabled = busy || node.dataset.locked === "true";
  });
  const ready = plan?.has_changes;
  byId("match").disabled = busy || !ready;
  byId("connection").textContent = busy
    ? "Operação em andamento…"
    : state
      ? `${state.monitors.length} monitores conectados`
      : "Aguardando leitura";
  document.body.setAttribute("aria-busy", String(busy));
  window.ControlInputs.sync();
}
async function run(work) {
  if (busy) return;
  busy = true;
  lock();
  try {
    await work();
  } catch (error) {
    plan = null;
    notice(
      error.message.replace(
        /^Error invoking remote method '[^']+': Error: /,
        "",
      ),
      true,
    );
    log(error.message);
  } finally {
    busy = false;
    lock();
  }
}
function invalidate() {
  plan = null;
  byId("comparison-count").textContent = "Prepare uma nova comparação";
  lock();
}
function renderPair() {
  for (const key of ["source", "target"]) {
    const profile = selected(key);
    byId(key + "-type").textContent = role(profile);
    byId(key + "-display").textContent = displayName(profile);
    byId(key + "-model").textContent = modelName(profile);
    byId(key + "-details").textContent = profile
      ? `${Object.keys(profile.values).length} controles legíveis · ${profile.tone_available ? "curva SDR disponível" : "curva SDR indisponível"}`
      : "Nenhum monitor disponível. Ative DDC/CI e atualize.";
  }
  byId("match").textContent =
    `Igualar ${role(selected("target"))} ao ${role(selected("source"))} →`;
}
function valueCell(value, className) {
  const cell = element("td", undefined, className);
  if (!value) {
    cell.textContent = "—";
    return cell;
  }
  cell.append(
    document.createTextNode(value.current),
    element("span", `/ ${value.maximum}`, "maximum"),
  );
  return cell;
}
function renderComparison() {
  const source = selected("source"),
    target = selected("target");
  const body = byId("comparison");
  body.replaceChildren();
  if (!source || !target) {
    const row = element("tr"),
      cell = element(
        "td",
        "Conecte duas telas com DDC/CI e clique em Atualizar.",
        "empty",
      );
    cell.colSpan = 5;
    row.append(cell);
    body.append(row);
    return;
  }
  for (const [key, label] of Object.entries(features)) {
    const a = source.values[key],
      b = target.values[key];
    const change = plan?.changes.find((c) => c.feature === key);
    const skipped =
      plan?.skipped[key] ||
      (!a || !b ? "Controle indisponível em uma das telas." : null);
    const next =
      !plan || skipped
        ? null
        : { current: change ? change.after : b.current, maximum: b.maximum };
    const row = element("tr");
    row.dataset.feature = key;
    row.append(
      element("td", label),
      valueCell(a),
      valueCell(b),
      valueCell(next, change ? "will-change" : ""),
    );
    const status = element(
      "td",
      skipped
        ? "Indisponível"
        : !plan
          ? "—"
          : change
            ? "Será copiado"
            : "Já igual",
      "comparison-state",
    );
    if (skipped) status.title = skipped;
    if (change) status.classList.add("will-change");
    row.append(status);
    body.append(row);
  }
  const tone = element("tr");
  const color = element("tr");
  color.append(
    element("td", "Modo de cor"),
    element("td", colorName(source.color_preset?.current)),
    element("td", colorName(target.color_preset?.current)),
    element("td", plan ? colorName(plan.color_target) : "—"),
    element(
      "td",
      !plan
        ? "—"
        : plan.skipped.color_preset
          ? "Indisponível"
          : plan.color
            ? "Habilitar RGB"
            : plan.color_target !== source.color_preset?.current
              ? "RGB editável"
              : "Já igual",
      "comparison-state",
    ),
  );
  body.append(color);
  const wantsTone = byId("copy-tone").checked;
  tone.append(
    element("td", "Curva de tons SDR"),
    element("td", source.tone_available ? "Disponível" : "—"),
    element("td", target.tone_available ? "Disponível" : "—"),
    element(
      "td",
      plan && wantsTone
        ? plan.tone
          ? "Igual à referência"
          : "Sem alteração"
        : "—",
    ),
    element(
      "td",
      !wantsTone
        ? "Fora da cópia"
        : !plan
          ? "—"
          : plan.tone
            ? "Será copiada"
            : "Já igual",
      plan?.tone ? "comparison-state will-change" : "comparison-state",
    ),
  );
  body.append(tone);
  const count = plan
    ? plan.changes.length +
      Number(Boolean(plan.tone)) +
      Number(Boolean(plan.color))
    : 0;
  const skipped = plan ? Object.keys(plan.skipped).length : 0;
  byId("comparison-count").textContent = plan
    ? `${count} ajuste${count === 1 ? "" : "s"} pendente${count === 1 ? "" : "s"}${skipped ? ` · ${skipped} indisponível` : ""}`
    : "Aguardando comparação";
  byId("action-title").textContent = !plan
    ? "Confira as opções e compare novamente."
    : count
      ? `${count} ajuste${count === 1 ? "" : "s"} para copiar da referência.`
      : skipped
        ? "Os controles compatíveis já estão iguais."
        : "Os controles de imagem já estão iguais.";
  byId("action-description").textContent =
    "O backup do destino é automático. O monitor de referência será preservado.";
}
function renderManual() {
  const profile = selected("target");
  const fields = byId("manual-fields");
  fields.replaceChildren();
  for (const [key, label] of Object.entries(features)) {
    const value = profile?.values[key];
    fields.append(
      window.ControlInputs.create({
        name: key,
        label,
        max: value?.maximum || 100,
        value: value?.current || 0,
        disabled: !value,
        compact: !["brightness", "contrast"].includes(key),
        description: {
          brightness: "Intensidade da luz de fundo do monitor.",
          contrast: "Separação dos tons. Confira os realces.",
          red: "Equilíbrio do vermelho.",
          green: "Equilíbrio do verde.",
          blue: "Equilíbrio do azul.",
        }[key],
      }),
    );
  }
  byId("draft-status").textContent = "Valores lidos";
  byId("draft-status").classList.remove("dirty");
  if (!byId("tone-fields").children.length) {
    byId("tone-fields").append(
      window.ControlInputs.create({
        name: "gamma",
        label: "Meios-tons",
        min: 0.85,
        max: 1.15,
        step: 0.01,
        value: 1,
        description: "Acima de 1 escurece meios-tons; abaixo de 1 clareia.",
      }),
      window.ControlInputs.create({
        name: "black_point",
        label: "Corte de sombras",
        min: 0,
        max: 4,
        step: 0.5,
        value: 0,
        description:
          "Corta níveis digitais perto do preto. Pode esconder detalhes.",
      }),
    );
  }
}
async function diagnose() {
  const profile = selected("target");
  if (!profile) return;
  const result = await api.diagnostics({ target: profile.monitor.id });
  const output = result.output;
  byId("range-title").textContent =
    output.range === "full"
      ? `${output.vendor} · RGB completo`
      : output.range === "limited"
        ? `${output.vendor} · RGB limitado`
        : "Faixa de saída não confirmada";
  byId("range-description").textContent =
    output.range === "full"
      ? `${output.bits || "?"} bits · o driver informa faixa completa. O nível físico de preto e o menu do monitor ainda precisam de avaliação visual.`
      : output.range === "limited"
        ? "O driver informa faixa limitada. Confira se ela corresponde à faixa esperada pelo monitor antes de mudar."
        : output.error ||
          `Formato ${output.format || "não informado"}. Confira a faixa no painel da GPU.`;
}
function readField(input) {
  const raw = input.value.trim().replace(",", ".");
  if (!raw) return null;
  const value = Number(raw),
    step = Number(input.dataset.step);
  if (
    !/^\d+(\.\d+)?$/.test(raw) ||
    !Number.isFinite(value) ||
    value < Number(input.dataset.min) ||
    value > Number(input.dataset.max) ||
    (step === 1 && !Number.isInteger(value))
  ) {
    input.setAttribute("aria-invalid", "true");
    input.focus();
    throw new Error(
      `Confira ${input.getAttribute("aria-label")}: use valores de ${input.dataset.min} a ${input.dataset.max}.`,
    );
  }
  return value;
}
async function compare() {
  invalidate();
  const source = selected("source"),
    target = selected("target");
  if (!source || !target) {
    renderComparison();
    return;
  }
  if (source.monitor.id === target.monitor.id && state.monitors.length === 1) {
    renderComparison();
    notice(
      "Uma tela conectada. Os ajustes individuais estão disponíveis; a cópia exige duas telas.",
    );
    return;
  }
  if (source.monitor.id === target.monitor.id) {
    renderComparison();
    notice(
      document.body.dataset.screen === "sync"
        ? "Selecione duas telas diferentes para copiar ajustes. Modelos e ajustes individuais continuam disponíveis."
        : "",
    );
    return;
  }
  plan = await api.previewMatch({
    source: source.monitor.id,
    target: target.monitor.id,
    mode: byId("mode").value,
    tone: byId("copy-tone").checked,
    color_mode: byId("color-mode").value,
  });
  previewKind = "match";
  renderComparison();
  notice("");
}
async function load() {
  const previous = {
    source: byId("source").value,
    target: byId("target").value,
  };
  state = await api.state();
  plan = null;
  byId("demo-banner").hidden = !state.demo;
  for (const key of ["source", "target"]) {
    const select = byId(key);
    select.replaceChildren();
    for (const profile of state.monitors) {
      const option = element(
        "option",
        `${displayName(profile)} · ${modelName(profile)} · ${role(profile)}`,
      );
      option.value = profile.monitor.id;
      select.append(option);
    }
    select.dataset.locked = String(!state.monitors.length);
    const wanted =
      state.monitors.find((p) => p.monitor.id === previous[key]) ||
      state.monitors.find(
        (p) => state.roles[p.monitor.id] === (key === "source" ? "ips" : "va"),
      ) ||
      state.monitors[
        key === "source" ? 0 : Math.min(1, state.monitors.length - 1)
      ];
    if (wanted) select.value = wanted.monitor.id;
  }
  byId("backup-directory").textContent = "Pasta local: " + state.backup_dir;
  renderPair();
  renderManual();
  renderComparison();
  for (const warning of state.warnings) log(warning);
  await compare();
  await diagnose();
}
function confirm(planTitle) {
  if (!plan?.has_changes) {
    notice("Nenhum ajuste precisa ser alterado.");
    return;
  }
  byId("confirm-title").textContent = planTitle;
  byId("confirm-target").textContent =
    `${displayName(selected("target"))} · ${plan.monitor.name}`;
  const changes = byId("confirm-changes");
  changes.replaceChildren();
  for (const change of plan.changes) {
    const item = element("li");
    item.append(
      element("span", features[change.feature]),
      element("strong", `${change.before} → ${change.after}`),
    );
    changes.append(item);
  }
  if (plan.tone) {
    const item = element("li");
    item.append(element("span", "Curva SDR"), element("strong", plan.tone));
    changes.append(item);
  }
  if (plan.color) {
    const item = element("li");
    item.append(
      element("span", "Modo de cor"),
      element(
        "strong",
        `${colorName(plan.color.before)} → ${colorName(plan.color.after)}`,
      ),
    );
    changes.append(item);
  }
  for (const [key] of Object.entries(plan.skipped))
    changes.append(
      element("li", `${labels[key]}: indisponível, não será copiado.`),
    );
  byId("confirm-extra").textContent = plan.notes
    .filter(
      (note) => previewKind === "preset" || /Usuário|curva|sombras/i.test(note),
    )
    .join(" ");
  byId("confirm").returnValue = "";
  byId("confirm").showModal();
}

byId("refresh").addEventListener("click", () => run(load));
for (const key of ["source", "target", "copy-tone", "mode", "color-mode"]) {
  byId(key).addEventListener("change", () =>
    run(async () => {
      renderPair();
      renderManual();
      if (key === "target") {
        byId("manual-tone").checked = false;
        await diagnose();
      }
      await compare();
    }),
  );
}
byId("match").addEventListener("click", () =>
  run(async () => {
    if (previewKind !== "match" || !plan) await compare();
    confirm("Igualar o destino à referência?");
  }),
);
byId("confirm").addEventListener("cancel", () => {
  plan = null;
  run(compare);
});
byId("confirm")
  .querySelector("form")
  .addEventListener("submit", (event) => {
    // Submit é síncrono. O evento close pode esperar um frame quando a janela está ocluída.
    event.preventDefault();
    const action = event.submitter?.value || "cancel";
    byId("confirm").close(action);
    if (action !== "apply") {
      plan = null;
      run(compare);
      return;
    }
    run(async () => {
      const token = plan.token;
      plan = null;
      const result = await api.apply({ token });
      if (result.backup) log("Backup automático: " + result.backup);
      if (!result.ok) {
        const error = Object.entries(result.failed)
          .map(([k, v]) => `${labels[k] || k}: ${v}`)
          .join(" ");
        await load();
        notice(`Aplicação incompleta. ${error} Backup: ${result.backup}`, true);
        log("Aplicação incompleta: " + error);
        return;
      }
      log(`${result.applied.length} ajuste(s) aplicado(s) e verificado(s).`);
      const previousKind = previewKind;
      await load();
      notice(
        previousKind === "match"
          ? "Cópia concluída. Os ajustes compatíveis do destino foram verificados com a referência."
          : "Ajustes aplicados e verificados. O backup anterior está salvo.",
      );
    });
  });
byId("manual-form").addEventListener("submit", (event) => {
  event.preventDefault();
  run(async () => {
    const values = {};
    for (const input of byId("manual-fields").querySelectorAll(
      "input[data-value]",
    )) {
      if (input.closest(".control-card").hidden) continue;
      if (input.dataset.locked !== "true") {
        const value = readField(input);
        if (value !== null) values[input.name] = value;
      }
    }
    let tone = null;
    if (byId("manual-tone").checked && !byId("tone-options").hidden) {
      tone = {};
      for (const input of byId("tone-fields").querySelectorAll(
        "input[data-value]",
      )) {
        const value = readField(input);
        if (value === null)
          throw new Error("Preencha os dois controles da curva SDR.");
        tone[input.name] = value;
      }
    }
    plan = await api.previewVisual({
      target: selected("target").monitor.id,
      values,
      tone,
    });
    previewKind = "manual";
    confirm("Aplicar os ajustes manuais?");
  });
});
byId("manual-form").addEventListener("input", () => {
  byId("draft-status").textContent = "Alterações não aplicadas";
  byId("draft-status").classList.add("dirty");
});
byId("manual-tone").addEventListener("change", lock);
byId("diagnose").addEventListener("click", () => run(diagnose));
byId("display-settings").addEventListener("click", () =>
  run(() => api.displaySettings()),
);
byId("compare-pattern").addEventListener("click", () =>
  run(() =>
    api.pattern({
      source: selected("source")?.monitor.id,
      target: selected("target")?.monitor.id,
      pair: true,
      mode: "black",
    }),
  ),
);
byId("undo").addEventListener("click", () =>
  run(async () => {
    plan = await api.previewUndo({ target: selected("target").monitor.id });
    previewKind = "undo";
    confirm("Voltar ao ajuste anterior?");
  }),
);
byId("backup").addEventListener("click", () =>
  run(async () => {
    const result = await api.backup({ target: selected("target").monitor.id });
    log("Backup manual: " + result.path);
    notice("Backup salvo: " + result.path);
  }),
);
byId("restore").addEventListener("click", () =>
  run(async () => {
    const result = await api.restore({ target: selected("target").monitor.id });
    if (!result) return;
    plan = result;
    previewKind = "restore";
    confirm("Restaurar os ajustes deste backup?");
  }),
);
byId("open-backups").addEventListener("click", () =>
  run(() => api.openBackups()),
);
byId("pattern").addEventListener("click", () =>
  run(() => api.pattern({ target: selected("target").monitor.id })),
);
for (const tab of document.querySelectorAll("[data-tab]")) {
  tab.addEventListener("click", () => {
    for (const item of document.querySelectorAll("[data-tab]")) {
      item.classList.toggle("active", item === tab);
      if (item === tab) item.setAttribute("aria-current", "page");
      else item.removeAttribute("aria-current");
    }
    for (const key of ["sync", "manual", "backups"])
      byId(key + "-view").hidden = key !== tab.dataset.tab;
    const titles = {
      sync: [
        "Seu IPS como referência.",
        "Copie os ajustes para o VA e use os dois como um par.",
      ],
      manual: [
        "Uma imagem do seu jeito.",
        "Ajuste a aparência do VA usando o IPS como referência visual.",
      ],
      backups: [
        "Um caminho de volta.",
        "Guarde seus ajustes e restaure quando precisar.",
      ],
    };
    [byId("page-title").textContent, byId("page-description").textContent] =
      titles[tab.dataset.tab];
    if (tab.dataset.tab === "sync" && (previewKind !== "match" || !plan))
      run(compare);
  });
}
run(load);
