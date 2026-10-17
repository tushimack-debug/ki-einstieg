'use strict';
// Filter für Landingpages: blendet die statisch gerenderten Karten ein/aus. Kein Tracking, keine Cookies.
(() => {
  const form = document.getElementById('landing-filters');
  const cards = [...document.querySelectorAll('#landing-jobs > .card')];
  if (!form || !cards.length) return;
  form.hidden = false;
  const q = document.getElementById('lf-search'), field = document.getElementById('lf-field'), remote = document.getElementById('lf-remote');
  const count = document.getElementById('lf-count');
  const params = new URLSearchParams(location.search);
  q.value = params.get('q') || ''; field.value = params.get('feld') || ''; if (remote) remote.checked = params.get('remote') === '1';
  function apply() {
    const words = q.value.trim().toLocaleLowerCase('de').split(/\s+/).filter(Boolean);
    let shown = 0;
    for (const card of cards) {
      const ok = words.every(w => card.dataset.search.includes(w))
        && (!field.value || card.dataset.fields.split('|').includes(field.value))
        && (!remote || !remote.checked || card.dataset.remote === '1');
      card.hidden = !ok; if (ok) shown++;
    }
    count.textContent = shown === cards.length ? '' : `${shown} von ${cards.length} Stellen`;
    const p = new URLSearchParams();
    if (q.value.trim()) p.set('q', q.value.trim()); if (field.value) p.set('feld', field.value); if (remote && remote.checked) p.set('remote', '1');
    history.replaceState(null, '', p.toString() ? `?${p}` : location.pathname);
  }
  form.addEventListener('submit', e => e.preventDefault());
  form.addEventListener('input', apply);
  apply();
})();
