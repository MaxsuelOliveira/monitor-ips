// Executar em uma instância DEMO própria via Agent Browser eval -b.
(async () => {
  const assert = (value, message) => { if (!value) throw new Error(message); };
  const settle = async () => {
    for (let i = 0; i < 240; i++) {
      if (!busy && state) return;
      await new Promise(resolve => setTimeout(resolve, 25));
    }
    throw new Error('Operation did not settle');
  };
  await settle(); assert(state.demo, 'Only demo is permitted');
  assert(document.getElementById('source').hidden, 'Native select must be hidden');
  assert(document.querySelectorAll('.select-trigger[role=combobox]').length === 4, 'Custom comboboxes missing');
  const sourceTrigger = document.getElementById('source-trigger');
  sourceTrigger.click();
  assert(sourceTrigger.getAttribute('aria-expanded') === 'true', 'Select did not open');
  sourceTrigger.dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}));
  assert(sourceTrigger.getAttribute('aria-expanded') === 'false', 'Escape did not close select');
  const input = document.querySelector('input[name=brightness]');
  const original = Number(input.value);
  document.querySelector('[data-control=brightness] .step-button:last-child').click();
  assert(Number(input.value) === original + 1, 'Stepper did not increment');
  assert(Number(document.querySelector('[data-control=brightness] input[type=range]').value) === original + 1, 'Slider did not synchronize');
  const unchanged = await api.state();
  assert(unchanged.monitors[1].values.brightness.current === original, 'Editing UI wrote hardware');
  input.value = '-1'; input.dispatchEvent(new Event('input', {bubbles:true}));
  document.getElementById('manual-form').requestSubmit(); await settle();
  assert(input.getAttribute('aria-invalid') === 'true', 'Out-of-range input was accepted');
  input.value = ''; input.dispatchEvent(new Event('input', {bubbles:true}));
  document.querySelector('input[name=contrast]').value = '61';
  document.getElementById('manual-form').requestSubmit(); await settle();
  assert(!plan.changes.some(c => c.feature === 'brightness'), 'Blank input became zero');
  const form = document.querySelector('dialog form');
  form.requestSubmit(form.querySelector('[value=cancel]')); await settle();
  document.querySelector('input[name=brightness]').value = '40';
  document.getElementById('tone-options').open = true;
  document.getElementById('manual-tone').click();
  document.querySelector('input[name=gamma]').value = '1,06';
  document.querySelector('input[name=black_point]').value = '0.5';
  document.getElementById('manual-form').requestSubmit(); await settle();
  assert(plan.tone, 'Tone preview missing');
  assert(document.getElementById('confirm-extra').textContent.includes('sombras'), 'Shadow detail warning missing');
  form.requestSubmit(document.getElementById('confirm-apply')); await settle();
  assert(selected('target').values.brightness.current === 40, 'Manual application failed');
  assert(!document.getElementById('undo').disabled, 'Undo not enabled');
  assert(selected('source').values.brightness.current === 35, 'Reference changed');
  document.getElementById('undo').click(); await settle();
  form.requestSubmit(document.getElementById('confirm-apply')); await settle();
  assert(selected('target').values.brightness.current === original, 'Undo did not restore DDC');
  assert(selected('target').tone_curve[0][128] === 128 * 257, 'Undo did not restore curve');
  assert(document.getElementById('range-title').textContent.includes('completo'), 'Diagnostic did not render');
  assert(document.documentElement.scrollWidth <= innerWidth, 'Horizontal overflow');
  return { ok: true, checked:['custom selects', 'keyboard', 'stepper/slider sync', 'no writes on edit', 'input bounds', 'blank preserved', 'curve warning', 'manual apply', 'undo DDC and tone', 'source preserved', 'range diagnostic', 'overflow'] };
})();
