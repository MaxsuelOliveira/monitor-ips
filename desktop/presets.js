/* Usa o catálogo Python e o mesmo fluxo de confirmação/backup do renderer. */
(() => {
  let targetId, catalogKey;
  const cards = byId("preset-cards");
  const panel = byId("preset-panel");
  const tone = byId("preset-tone");
  const custom = byId("preset-custom");
  const brightness = window.ControlInputs.create({
    name: "preset-brightness-value",
    label: "Brilho personalizado",
    description: "Percentual da escala DDC; não é luminância em cd/m².",
    value: 22,
    min: 0,
    max: 100,
    step: 1,
  });
  byId("preset-brightness").append(brightness);

  function render() {
    const profile = selected("target");
    const id = profile?.monitor.id;
    if (id !== targetId) {
      targetId = id;
      const known = state?.roles[id];
      panel.value = known === "va" ? "va" : "ips";
      byId("preset-panel-hint").textContent = known
        ? "Tipo registrado localmente. Confira antes de aplicar."
        : "Tipo não identificado. Selecione IPS ou VA conforme seu monitor.";
      custom.checked = false;
      tone.checked = Boolean(profile?.tone_available);
    }
    const entries = state?.presets || [];
    const key = JSON.stringify(entries);
    if (catalogKey !== key) {
      catalogKey = key;
      cards.replaceChildren();
      for (const [index, preset] of entries.entries()) {
        const label = element("label", undefined, "preset-card");
        const input = element("input");
        input.type = "radio";
        input.name = "image-preset";
        input.value = preset.id;
        input.checked = index === 0;
        const content = element("span", undefined, "preset-card-content");
        content.append(
          element("span", preset.environment, "preset-environment"),
          element("strong", preset.name),
          element("span", preset.description, "preset-description"),
        );
        label.append(input, content);
        cards.append(label);
      }
    }
    const preset = entries.find(
      (item) => item.id === cards.querySelector("input:checked")?.value,
    );
    byId("preset-review").dataset.locked = String(!profile || !preset);
    byId("preset-review").disabled = busy || !profile || !preset;
    tone.disabled = busy || !profile?.tone_available;
    if (!profile?.tone_available) tone.checked = false;
    tone.dataset.locked = String(!profile?.tone_available);
    byId("preset-tone-hint").textContent = profile?.tone_available
      ? "Substitui a curva atual dos três canais. O backup permite restaurá-la."
      : "Curva SDR indisponível. Sem ela, o modelo ajusta somente o brilho.";
    byId("preset-brightness").hidden = !custom.checked;
    if (preset) {
      const percent = preset.brightness[panel.value];
      const policy =
        preset.brightness_mode === "ceiling" ? "teto de" : "alvo de";
      const parts = [
        `${preset.name} em ${panel.value.toUpperCase()}: ${custom.checked ? "brilho personalizado" : `${policy} brilho ${percent}% da escala DDC`}.`,
      ];
      if (!custom.checked && preset.brightness_mode === "ceiling")
        parts.push("Mantém o brilho atual quando ele já é menor.");
      parts.push(
        tone.checked
          ? "Inclui curva SDR absoluta, sem acumular o efeito."
          : "Somente brilho; a curva atual será preservada.",
      );
      parts.push("RGB, contraste e modo de cor preservados.");
      byId("preset-summary").textContent = parts.join(" ");
    }
    window.ControlInputs.sync();
  }
  byId("preset-form").addEventListener("change", render);
  byId("target").addEventListener("change", render);
  new MutationObserver(render).observe(document.body, {
    attributes: true,
    attributeFilter: ["aria-busy"],
  });
  byId("preset-form").addEventListener("submit", (event) => {
    event.preventDefault();
    run(async () => {
      const chosen = cards.querySelector("input:checked")?.value;
      const params = {
        target: byId("target").value,
        preset: chosen,
        panel: panel.value,
        tone: tone.checked,
      };
      if (custom.checked) {
        params.brightness = readField(
          brightness.querySelector("input[data-value]"),
        );
        if (params.brightness === null)
          throw new Error("Preencha o brilho personalizado.");
      }
      plan = await api.previewPreset(params);
      previewKind = "preset";
      confirm("Aplicar este modelo no destino selecionado?");
    });
  });
  render();
})();
