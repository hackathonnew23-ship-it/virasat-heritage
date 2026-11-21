/* Connects the web app to the Virasat FastAPI backend (same origin when served by uvicorn).
   If the API is unreachable (e.g. opened as a plain file) the bundled demo data keeps working. */
(function () {
  const B = window.API_BASE || '';
  let SR = null;
  const toD = s => ({ id: s.id, t: s.title, pl: [s.place, s.state].filter(Boolean).join(', '), la: s.lat, lo: s.lon,
    c: s.category, ph: s.photo_count, nat: s.native_name, tx: s.description });
  async function loadSites() {
    const r = await fetch(B + '/api/sites'); if (!r.ok) throw new Error(r.status);
    const rows = await r.json(); D.splice(0, D.length, ...rows.map(toD)); render();
  }
  score = function (d, qt, q) { return !q || !q.trim() ? 1 : ((SR && SR.get(d.id)) || 0); };
  let timer;
  $('#q').oninput = () => { clearTimeout(timer); timer = setTimeout(async () => {
    const q = $('#q').value.trim();
    if (!q) { SR = null; return render(); }
    try { const r = await fetch(B + '/api/search?limit=50&q=' + encodeURIComponent(q));
      SR = new Map((await r.json()).map(h => [h.id, h.score])); } catch (e) { SR = null; }
    render(); }, 150); };
  const prev = $('#sub').onclick;
  $('#sub').onclick = async e => {
    const isNote = $('#sub').textContent.startsWith('Add note'), title = $('#f_t').value.trim();
    const body = { title, lat: +$('#f_la').value, lon: +$('#f_lo').value, category: $('#f_c').value,
      description: $('#f_n').value, photo_count: +$('#f_p').value || 0 };
    const site = D.find(x => x.t === title); prev(e);
    try {
      if (isNote && site) await fetch(B + '/api/sites/' + site.id + '/notes', { method: 'POST',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ body: body.description, photos_added: body.photo_count }) });
      else if (!isNote) { await fetch(B + '/api/sites', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); await loadSites(); }
    } catch (err) { console.warn('API write failed; kept locally', err); }
  };
  // Real OCR: upload your own scan
  const box = document.createElement('div');
  box.innerHTML = "<p class='mu'>Or upload your own scan (PNG/JPG) for real OCR via the backend:</p><input type='file' id='ocrfile' accept='image/*'>";
  $('#cv').after(box);
  $('#ocrfile').onchange = async ev => {
    const f = ev.target.files[0]; if (!f) return; const fd = new FormData(); fd.append('file', f);
    $('#ocrout').innerHTML = "<p class='mu'>Uploading and running OCR\u2026</p>";
    try {
      const r = await fetch(B + '/api/ocr', { method: 'POST', body: fd }); const j = await r.json();
      if (!r.ok) throw new Error(j.detail || r.status);
      $('#ocrout').innerHTML = `<b>Transcription</b> <span class='tag'>${j.script} \u00b7 ${j.language} ${j.confidence}%</span><p class='native'>${j.text.replace(/</g, '&lt;')}</p><b>Entities</b><p>${j.entities.map(x => `<span class='tag'>${x.type}: ${x.value}</span>`).join('') || '<span class=mu>none found</span>'}</p><p class='mu'>Engine: ${j.engine}. Saved as document #${j.document_id} and now searchable.</p>`;
    } catch (err) { $('#ocrout').innerHTML = "<p class='mu'>OCR needs the backend running: " + err.message + "</p>"; }
  };
  loadSites().catch(() => console.info('Backend not reachable - using bundled demo data'));
})();
