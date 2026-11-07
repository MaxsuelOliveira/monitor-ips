// Executar via Agent Browser eval -b, somente no Electron DEMO próprio.
(async () => {
  async function settle() {
    for (let i = 0; i < 200; i++) {
      if (!busy && state) return;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
    throw new Error("UI operation did not settle");
  }
  function assert(condition, message) {
    if (!condition) throw new Error(message);
  }
  await settle();
  assert(state.demo === true, "QA writes require demo backend");
  const original = selected("target").values.brightness.current;
  document.querySelector('[data-tab="manual"]').click();
  document.querySelector('input[name="brightness"]').value = "";
  document.querySelector('input[name="contrast"]').value = "61";
  document.getElementById("manual-form").requestSubmit();
  await settle();
  assert(previewKind === "manual", "Manual preview missing");
  assert(!plan.changes.some((c) => c.feature === "brightness"), "Blank input must not become zero");
  const form = document.querySelector("dialog form");
  form.requestSubmit(form.querySelector('[value="cancel"]'));
  await settle();
  assert(previewKind === "match", "Cancel must discard manual plan");
  assert(selected("target").values.brightness.current === original, "Cancel wrote to target");
  document.querySelector('[data-tab="sync"]').click();
  document.getElementById("mode").value = "relative";
  document.getElementById("mode").dispatchEvent(new Event("change"));
  await settle();
  assert(plan.changes.find((c) => c.feature === "brightness").after === 70, "Relative mode incorrect");
  document.getElementById("mode").value = "exact";
  document.getElementById("mode").dispatchEvent(new Event("change"));
  await settle();
  assert(plan.changes.find((c) => c.feature === "brightness").after === 35, "Exact mode incorrect");
  document.getElementById("match").click();
  await settle();
  form.requestSubmit(document.getElementById("confirm-apply"));
  await settle();
  assert(selected("target").values.brightness.current === 35, "Confirmation did not apply");
  assert(selected("source").values.brightness.current === 35, "Source changed");
  assert(!plan.has_changes, "Match should be idempotent");
  assert(document.documentElement.scrollWidth <= innerWidth, "Horizontal overflow");
  return { ok: true, checked: ["blank fields", "cancel preview", "relative vs exact", "confirmation", "source untouched", "idempotence", "overflow"] };
})();
