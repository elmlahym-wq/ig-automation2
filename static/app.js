const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
async function api(path, method = "GET", body) {
  const r = await fetch(path, {method, headers: {"Content-Type": "application/json"}, body: body ? JSON.stringify(body) : undefined});
  if (!r.ok) { let m = r.statusText; try { const j = await r.json(); m = typeof j.detail === "string" ? j.detail : "Please check the form fields"; } catch {} throw new Error(m); }
  return r.status === 204 ? null : r.json();
}
function toast(msg, err) { const t = $("#toast"); t.textContent = msg; t.className = "show" + (err ? " err" : ""); setTimeout(() => t.className = "", 2800); }

async function initSettings() {
  const f = $("#settings-form");
  const c = await api("/api/config");
  f.page_id.value = c.page_id; f.ig_account_id.value = c.ig_account_id;
  $("#token-hint").textContent = c.token_set ? "A token is configured. Leave blank to keep it." : "No token saved yet.";
  f.onsubmit = async e => {
    e.preventDefault();
    try { await api("/api/config", "PUT", Object.fromEntries(new FormData(f))); f.access_token.value = ""; toast("Settings saved"); initSettings(); }
    catch (err) { toast(err.message, true); }
  };
}

async function initCampaigns() {
  const dlg = $("#dlg"), f = $("#campaign-form"), prev = $("#preview");
  let items = [];
  async function load() { items = await api("/api/campaigns"); render(); }
  function render() {
    $("#list").innerHTML = items.length ? items.map(c => `
      <div class="camp"><div class="meta"><strong>${esc(c.name || "Post " + c.post_id)}</strong>
        <span class="badge ${c.active ? "on" : "off"}">${c.active ? "Active" : "Inactive"}</span></div>
        <div>${c.keywords.split(",").map(k => k.trim() && `<span class="kw">${esc(k.trim())}</span>`).join("")}</div>
        <p><b>Reply:</b> ${esc(c.comment_reply)}</p><p><b>DM:</b> ${esc(c.dm_message)}</p>
        <div class="actions"><button class="btn sm" data-a="toggle" data-id="${c.id}">${c.active ? "Pause" : "Activate"}</button>
        <button class="btn sm" data-a="edit" data-id="${c.id}">Edit</button>
        <button class="btn sm danger" data-a="del" data-id="${c.id}">Delete</button></div></div>`).join("")
      : `<div class="empty">No campaigns yet. Create one to start replying to comments automatically.</div>`;
  }
  function open(c) {
    f.reset(); prev.hidden = true;
    $("#dlg-title").textContent = c ? "Edit campaign" : "New campaign";
    if (c) { for (const k of ["id","name","post_id","keywords","comment_reply","dm_message"]) f[k].value = c[k] ?? ""; f.active.checked = c.active; }
    dlg.showModal();
  }
  $("#new-btn").onclick = () => open(null);
  $("#cancel").onclick = () => dlg.close();
  $("#list").onclick = async e => {
    const b = e.target.closest("button"); if (!b) return;
    const id = +b.dataset.id;
    try {
      if (b.dataset.a === "edit") open(items.find(c => c.id === id));
      if (b.dataset.a === "toggle") { await api(`/api/campaigns/${id}/toggle`, "POST"); await load(); }
      if (b.dataset.a === "del" && confirm("Delete this campaign?")) { await api(`/api/campaigns/${id}`, "DELETE"); await load(); toast("Campaign deleted"); }
    } catch (err) { toast(err.message, true); }
  };
  f.post_id.onblur = async () => {
    const id = f.post_id.value.trim(); if (!id) return;
    prev.hidden = false; prev.className = "preview"; prev.textContent = "Loading preview…";
    try {
      const p = await api(`/api/post/${encodeURIComponent(id)}`);
      prev.innerHTML = `${p.thumbnail_url ? `<img src="${esc(p.thumbnail_url)}" alt="">` : ""}<div>${esc((p.caption || "No caption").slice(0, 140))}<br><a href="${esc(p.permalink)}" target="_blank" rel="noopener">Open post</a></div>`;
    } catch (err) { prev.className = "preview err"; prev.textContent = "Couldn't load post: " + err.message; }
  };
  f.onsubmit = async e => {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(f)); const id = d.id; delete d.id; d.active = f.active.checked;
    try { await api(id ? `/api/campaigns/${id}` : "/api/campaigns", id ? "PUT" : "POST", d); dlg.close(); await load(); toast("Campaign saved"); }
    catch (err) { toast(err.message, true); }
  };
  await load();
}

const page = document.body.dataset.page;
if (page === "settings") initSettings().catch(e => toast(e.message, true));
if (page === "campaigns") initCampaigns().catch(e => toast(e.message, true));
