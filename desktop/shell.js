/* Navegação e configuração inicial. As escritas continuam no renderer/serviço. */
(() => {
  const $ = (id) => document.getElementById(id);
  const make = (tag, text, cls) => {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (cls) el.className = cls;
    return el;
  };
  const pages = {
    presets: ["Modelos prontos", "Uma aparência para cada ambiente. Escolha o modelo e revise no destino."],
    brightness: ["Brilho", "Encontre uma intensidade confortável."],
    contrast: ["Contraste", "Equilibre os tons claros e escuros."],
    colors: ["Cores", "Ajuste o equilíbrio entre vermelho, verde e azul."],
    sync: ["Copiar ajustes", "Use sua tela IPS como referência para o destino."],
    compare: ["Comparar telas", "Observe o preto, as sombras e os realces nas duas telas."],
    backups: ["Backups", "Guarde seus ajustes e volte a eles quando precisar."],
    advanced: ["Avançado", "Ajustes opcionais da curva de tons, apenas em SDR."],
  };
  let current = "brightness", step = 0;
  const header = document.querySelector(".app-header");
  const nav = header.querySelector("nav");
  nav.replaceChildren();
  const controls = Object.keys(pages);
  for (const key of controls) {
    const button = make("button", pages[key][0], "tab");
    const icon = make("img");
    icon.src = "assets/icons/" + ({ presets: "palette", brightness: "sun", contrast: "circle-half", colors: "palette", sync: "copy", compare: "display", backups: "archive", advanced: "gear" })[key] + ".svg";
    icon.alt = "";
    button.prepend(icon);
    button.type = "button";
    button.dataset.screen = key;
    button.addEventListener("click", () => navigate(key, true));
    nav.append(button);
  }
  const setupButton = make("button", "Configurar telas", "secondary setup-link");
  setupButton.type = "button";
  setupButton.addEventListener("click", () => openSetup());
  header.append(setupButton);

  // Reutiliza os controles e eventos reais, sem uma segunda implementação de ajustes.
  const main = document.querySelector("main");
  const pair = document.querySelector(".pair");
  const destination = document.querySelector(".destination");
  const reference = document.querySelector(".reference");
  const scope = make("div", null, "destination-scope");
  const sourceHome = make("div", null, "source-home");
  $("sync-view").prepend(sourceHome);
  document.querySelector(".page-title").before(scope);
  scope.append(destination);
  sourceHome.append(reference);
  pair.remove();

  const compareView = make("section", null, "view");
  compareView.id = "compare-view";
  compareView.hidden = true;
  compareView.append(document.querySelector(".visual-guide"));
  $("manual-view").after(compareView);
  $("backups-view").append(document.querySelector(".undo-strip"));
  const tone = $("tone-options");
  const manualHeading = document.querySelector("#manual-form .section-heading");
  manualHeading.querySelector("h2").textContent = "Ajuste do monitor";
  const submit = manualHeading.querySelector("button[type=submit]");
  submit.textContent = "Revisar alteração";
  const submitHome = make("div", null, "focused-action");
  submitHome.append(submit, $("draft-status"));
  $("manual-form").append(submitHome);
  manualHeading.remove();

  const welcome = make("section", null, "welcome-screen");
  welcome.id = "welcome-screen";
  const image = make("img");
  image.src = "assets/welcome-monitors.png";
  image.alt = "Dois monitores exibindo a mesma paisagem de montanhas e lago";
  image.width = 700;
  image.height = 336;
  const welcomeTitle = make("h1", "Suas telas, do seu jeito.");
  const start = make("button", "Configurar minhas telas", "primary");
  start.type = "button";
  start.id = "setup-start";
  start.addEventListener("click", () => openSetup());
  const skip = make("button", "Agora não", "text-button");
  skip.type = "button";
  skip.addEventListener("click", () => finishSetup(false));
  welcome.append(image, welcomeTitle, make("p", "Ajuste o brilho, o contraste e as cores. Uma tela de cada vez."), start, skip);
  main.prepend(welcome);

  const wizard = make("section", null, "setup-screen");
  wizard.id = "setup-screen";
  wizard.hidden = true;
  const progress = make("ol", null, "setup-progress");
  for (const label of ["Referência", "Destino", "Revisão"]) progress.append(make("li", label));
  const wizardTitle = make("h1");
  wizardTitle.tabIndex = -1;
  const help = make("p", null, "muted");
  const choices = make("div", null, "setup-choices");
  const summary = make("p", null, "setup-summary");
  const validation = make("p", null, "setup-validation");
  validation.setAttribute("role", "status");
  const actions = make("div", null, "setup-actions");
  const back = make("button", "Voltar", "secondary");
  back.type = "button";
  back.addEventListener("click", () => {
    if (step === 0) { wizard.hidden = true; welcome.hidden = false; document.body.dataset.screen = "welcome"; start.focus(); }
    else { step--; renderSetup(); }
  });
  const next = make("button", "Continuar", "primary");
  next.type = "button";
  next.id = "setup-next";
  next.addEventListener("click", () => {
    const source = $("source").value, target = $("target").value;
    if (busy || !state?.monitors.length) return;
    if (step === 1 && (!target || (state.monitors.length > 1 && source === target))) {
      validation.textContent = "Escolha um destino diferente da referência.";
      return;
    }
    if (step < 2) { step++; renderSetup(); }
    else finishSetup(true);
  });
  actions.append(back, next);
  wizard.append(progress, wizardTitle, help, choices, summary, validation, actions);
  welcome.after(wizard);

  function navigate(key, focus = false) {
    current = key;
    document.body.dataset.screen = key;
    document.body.classList.remove("onboarding");
    welcome.hidden = wizard.hidden = true;
    for (const [name, view] of [["presets", $("presets-view")], ["sync", $("sync-view")], ["backups", $("backups-view")], ["compare", compareView]]) view.hidden = name !== key;
    $("manual-view").hidden = !["brightness", "contrast", "colors", "advanced"].includes(key);
    $("manual-form").dataset.function = key;
    $("page-title").textContent = pages[key][0];
    $("page-description").textContent = pages[key][1];
    document.querySelectorAll("[data-screen]").forEach((button) => {
      const active = button.dataset.screen === key;
      button.classList.toggle("active", active);
      if (active) button.setAttribute("aria-current", "page");
      else button.removeAttribute("aria-current");
    });
    filterFields();
    if (focus) { $("page-title").tabIndex = -1; $("page-title").focus(); }
    if (key === "sync" && (previewKind !== "match" || !plan)) run(compare);
  }
  function filterFields() {
    for (const card of $("manual-fields").children) {
      const key = card.dataset.control;
      card.hidden = !(current === key || (current === "colors" && ["red", "green", "blue"].includes(key)));
      if (card.querySelector("input[data-value]")?.dataset.locked === "true" && !card.querySelector(".unavailable-hint")) {
        card.append(make("p", "Indisponível neste monitor.", "unavailable-hint"));
      }
    }
    tone.hidden = current !== "advanced";
    updateDraftStatus();
  }
  function updateDraftStatus() {
    const visible = [...$("manual-fields").children].filter((card) => !card.hidden);
    const inputs = visible.flatMap((card) => [...card.querySelectorAll("input[data-value]")]);
    const profile = selected("target");
    const changed = inputs.some((input) => input.dataset.locked !== "true" && Number(input.value.replace(",", ".")) !== profile?.values[input.name]?.current);
    $("draft-status").textContent = changed ? "Alteração não aplicada" : "Valores lidos";
    $("draft-status").classList.toggle("dirty", changed);
    const available = current === "advanced" ? Boolean(profile?.tone_available) : inputs.some((input) => input.dataset.locked !== "true");
    submit.dataset.locked = String(!available);
    submit.disabled = busy || !available;
    if (current === "advanced" && $("manual-tone").checked) $("draft-status").textContent = "Curva SDR selecionada";
  }
  $("manual-form").addEventListener("input", updateDraftStatus);
  new MutationObserver(filterFields).observe($("manual-fields"), { childList: true });

  function openSetup() {
    step = 0;
    document.body.classList.add("onboarding");
    document.body.dataset.screen = "setup";
    welcome.hidden = true;
    wizard.hidden = false;
    renderSetup();
  }
  function renderSetup() {
    [...progress.children].forEach((item, i) => {
      item.classList.toggle("active", i === step);
      if (i === step) item.setAttribute("aria-current", "step");
      else item.removeAttribute("aria-current");
    });
    wizardTitle.textContent = ["Qual é sua tela de referência?", "Qual tela você quer ajustar?", "Tudo certo para começar?"][step];
    help.textContent = ["Você escolhe qual monitor é IPS. Ele será apenas lido.", "Somente o destino receberá suas alterações.", "Esta configuração seleciona suas telas. Nenhum ajuste será aplicado agora."][step];
    choices.replaceChildren();
    summary.hidden = step !== 2;
    choices.hidden = step === 2;
    validation.textContent = "";
    const key = step === 0 ? "source" : "target";
    for (const option of $(key).options) {
      const label = make("label", null, "monitor-choice");
      const icon = make("img");
      icon.src = "assets/monitor-preview.png";
      icon.alt = "";
      const input = make("input");
      input.type = "radio";
      input.name = "setup-monitor";
      input.value = option.value;
      input.checked = option.selected;
      input.disabled = busy || (key === "target" && state?.monitors.length > 1 && option.value === $("source").value);
      input.addEventListener("change", () => {
        $(key).value = input.value;
        // A mudança usa o mesmo evento da seleção normal: invalida planos e relê rascunhos.
        $(key).dispatchEvent(new Event("change", { bubbles: true }));
        renderSetup();
      });
      label.append(icon, make("span", option.textContent), input);
      choices.append(label);
    }
    if (state?.monitors.length === 1) validation.textContent = "Uma tela conectada. Você pode ajustá-la; copiar e comparar exige duas telas.";
    else if (!state?.monitors.length) validation.textContent = busy ? "Lendo seus monitores…" : "Nenhum monitor disponível. Ative DDC/CI e use Atualizar monitores.";
    summary.textContent = `Referência: ${$("source").selectedOptions[0]?.textContent || "—"}\nDestino: ${$("target").selectedOptions[0]?.textContent || "—"}`;
    next.textContent = step === 2 ? "Começar a ajustar" : "Continuar";
    next.disabled = busy || !state?.monitors.length;
  }
  function finishSetup(remember) {
    if (remember) {
      try { localStorage.setItem("monitor-ips-setup", JSON.stringify({ source: $("source").value, target: $("target").value })); } catch { /* Sem armazenamento, a sessão continua normalmente. */ }
    }
    navigate("brightness", true);
  }
  // Atualiza o assistente após leituras/locks sem timer ou processo permanente.
  let restored = false;
  new MutationObserver(() => {
    if (!restored && state) {
      restored = true;
      let saved;
      try { saved = JSON.parse(localStorage.getItem("monitor-ips-setup")); } catch { /* Configuração inválida: exibir boas-vindas. */ }
      if (saved && ["source", "target"].every((key) => [...$(key).options].some((o) => o.value === saved[key])) && (state.monitors.length === 1 || saved.source !== saved.target)) {
        $("source").value = saved.source;
        $("target").value = saved.target;
        renderPair(); renderManual();
        window.ControlInputs.sync();
        navigate("brightness");
        // load() já preparou o par anterior. Invalida-o para impedir prévia divergente.
        plan = null;
      }
    }
    if (!wizard.hidden) renderSetup();
  }).observe(document.body, { attributes: true, attributeFilter: ["aria-busy"] });
  document.body.classList.add("onboarding");
  document.body.dataset.screen = "welcome";
  $("refresh").textContent = "Atualizar monitores";
  const retry = make("button", "Atualizar monitores", "text-button");
  retry.type = "button";
  retry.addEventListener("click", () => run(load));
  wizard.append(retry);
  filterFields();
})();
