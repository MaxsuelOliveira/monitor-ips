// Agent Browser eval -b, somente na instância própria DEMO.
(async () => {
  const assert = (ok, message) => {
    if (!ok) throw new Error(message);
  };
  const settle = async () => {
    for (let i = 0; i < 240; i++) {
      if (!busy && state) return;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
    throw new Error("Operação não terminou");
  };
  await settle();
  assert(state.demo, "DEMO required");
  document.querySelector("[data-screen=presets]").click();
  const initial = await api.state();
  assert(initial.presets.length === 4, "Catalog missing");
  for (const [target, panel] of [
    ["demo-ips", "ips"],
    ["demo-va", "va"],
  ]) {
    byId("target").value = target;
    byId("target").dispatchEvent(new Event("change", { bubbles: true }));
    await settle();
    assert(byId("preset-panel").value === panel, "Panel did not follow target");
    for (const preset of initial.presets) {
      const baseline = await api.state();
      const unchanged = baseline.monitors.find((m) => m.monitor.id !== target);
      document
        .querySelector(`input[name=image-preset][value="${preset.id}"]`)
        .click();
      byId("preset-tone").checked = true;
      byId("preset-form").requestSubmit();
      await settle();
      assert(byId("confirm").open, "Preview not shown");
      assert(plan.monitor.id === target, "Wrong destination");
      assert(previewKind === "preset", "Wrong preview kind");
      assert(
        byId("confirm-extra").textContent.includes("não se tornam idênticos"),
        "Limit missing",
      );
      const before = await api.state();
      assert(
        JSON.stringify(before.monitors.map((m) => m.values)) ===
          JSON.stringify(baseline.monitors.map((m) => m.values)),
        "Preview wrote controls",
      );
      const dialogForm = byId("confirm").querySelector("form");
      dialogForm.requestSubmit(dialogForm.querySelector("[value=apply]"));
      await settle();
      const after = await api.state();
      const other = after.monitors.find((m) => m.monitor.id !== target);
      assert(
        JSON.stringify(other.values) === JSON.stringify(unchanged.values),
        "Other display changed",
      );
      const profile = after.monitors.find((m) => m.monitor.id === target);
      assert(profile.can_undo, "Undo missing");
      for (const name of ["contrast", "red", "green", "blue"]) {
        const previous = baseline.monitors.find((m) => m.monitor.id === target);
        assert(
          JSON.stringify(profile.values[name]) ===
            JSON.stringify(previous.values[name]),
          "RGB/contrast changed",
        );
      }
      byId("undo").click();
      await settle();
      assert(byId("confirm").open, "Undo preview missing");
      dialogForm.requestSubmit(dialogForm.querySelector("[value=apply]"));
      await settle();
      const restored = (await api.state()).monitors.find(
        (m) => m.monitor.id === target,
      );
      const original = baseline.monitors.find((m) => m.monitor.id === target);
      assert(
        JSON.stringify(restored.values) === JSON.stringify(original.values),
        "Undo controls failed",
      );
      assert(
        JSON.stringify(restored.tone_curve) ===
          JSON.stringify(original.tone_curve),
        "Undo curve failed",
      );
    }
  }
  byId("preset-custom").checked = true;
  byId("preset-custom").dispatchEvent(new Event("change", { bubbles: true }));
  const input = document.querySelector("#preset-brightness input[data-value]");
  input.value = "101";
  byId("preset-form").requestSubmit();
  await settle();
  assert(
    input.getAttribute("aria-invalid") === "true",
    "Invalid override accepted",
  );
  input.value = "25";
  byId("preset-tone").checked = false;
  byId("preset-form").requestSubmit();
  await settle();
  assert(
    plan.changes.find((c) => c.feature === "brightness")?.after === 50,
    "Native maximum not scaled",
  );
  assert(!plan.tone, "No-tone ignored");
  const form = byId("confirm").querySelector("form");
  form.requestSubmit(form.querySelector("[value=cancel]"));
  await settle();
  assert(!byId("confirm").open, "Cancel failed");
  return {
    ok: true,
    checked: [
      "4 models on IPS and VA",
      "preview has no writes",
      "GUI apply",
      "RGB/contrast preserved",
      "other monitor unchanged",
      "undo DDC and curve",
      "override bounds",
      "native scaling",
      "no-tone",
      "cancel",
    ],
  };
})();
