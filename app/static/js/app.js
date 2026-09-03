/* Madad — app bootstrap: router, auth UI state, nav, delegated events */

const App = (() => {
  const view = document.getElementById('view');

  function setNav() {
    const authed = API.isAuthed();
    const u = API.user();
    document.querySelectorAll('.auth-only').forEach(el => el.classList.toggle('hidden', !authed));
    document.querySelectorAll('.guest-only').forEach(el => el.classList.toggle('hidden', authed));
    document.querySelectorAll('.admin-only').forEach(el => el.classList.toggle('hidden', !(authed && u && u.role === 'admin')));
    document.getElementById('btn-logout').textContent = u ? 'Log out · ' + u.name.split(' ')[0] : 'Log out';
  }

  function navActive() {
    const route = location.hash.replace(/^#\/?/, '') || 'home';
    const base = route.split('?')[0].split('/')[0];
    document.querySelectorAll('.nav-links a').forEach(a => {
      a.classList.toggle('active', a.dataset.nav === base);
    });
  }

  async function render() {
    UI.closeModal();
    const route = location.hash.replace(/^#\/?/, '') || 'home';
    const qIndex = route.indexOf('?');
    const pathPart = qIndex >= 0 ? route.slice(0, qIndex) : route;
    const queryPart = qIndex >= 0 ? route.slice(qIndex + 1) : '';
    const parts = pathPart.split('/').filter(Boolean);
    const base = parts[0] || 'home';
    let html = '<div class="loading-row"><div class="spinner"></div></div>';
    view.innerHTML = html;
    try {
      if (base === 'home') html = await vHome();
      else if (base === 'explore') {
        const p = new URLSearchParams(queryPart);
        html = await vExplore({
          cat: p.get('cat') || '',
          city: p.get('city') || '',
          q: p.get('q') || '',
          sort: p.get('sort') || 'recent',
        });
      } else if (base === 'c' && parts[1]) html = await vCampaign(decodeURIComponent(parts[1]));
      else if (base === 'login') html = await vLogin();
      else if (base === 'register') html = await vRegister();
      else if (base === 'dashboard') html = await vDashboard();
      else if (base === 'campaign' && parts[1] === 'new') {
        if (!API.isAuthed()) { location.hash = '#/login'; return; }
        html = await vNewCampaign();
      } else if (base === 'pledges' && parts[1]) {
        if (!API.isAuthed()) { location.hash = '#/login'; return; }
        html = await vPledges(decodeURIComponent(parts[1]));
      } else if (base === 'admin') html = await vAdmin();
      else html = await vHome();
      view.innerHTML = html;
      afterRender(base, parts);
    } catch (e) {
      view.innerHTML = `<div class="empty" style="margin-top:60px;"><div class="ico">😕</div><h4>Kuch ghalat ho gaya</h4><p class="small">${UI.esc(e.message)}</p><button class="btn btn-primary mt-12" onclick="location.reload()">Try again</button></div>`;
      UI.err(e);
    }
    window.scrollTo({ top: 0 });
  }

  function afterRender(base, parts) {
    // explore filters
    document.querySelectorAll('[data-cat-btn]').forEach(b => {
      b.addEventListener('click', () => exploreGo({ cat: b.dataset.catBtn }));
    });
    const applyBtn = document.getElementById('f-apply');
    if (applyBtn) applyBtn.addEventListener('click', () => {
      exploreGo({
        q: document.getElementById('f-search').value,
        city: document.getElementById('f-city').value,
        sort: document.getElementById('f-sort').value,
      });
    });
    const srch = document.getElementById('f-search');
    if (srch) srch.addEventListener('keydown', (e) => { if (e.key === 'Enter') applyBtn && applyBtn.click(); });

    // auth forms
    const aSubmit = document.getElementById('a-submit');
    if (aSubmit) {
      aSubmit.addEventListener('click', async () => {
        const isLogin = location.hash.includes('login');
        const email = document.getElementById('a-email').value.trim();
        const pass = document.getElementById('a-pass').value;
        const name = document.getElementById('a-name');
        const errEl = document.getElementById('a-err');
        errEl.textContent = '';
        if (!email || !pass || (!isLogin && (!name || !name.value.trim()))) {
          errEl.textContent = 'Please fill all required fields.'; return;
        }
        UI.btnLoading(aSubmit, true);
        try {
          const body = isLogin ? { email, password: pass } : { name: name.value.trim(), email, password: pass };
          const data = await API.post('/auth/' + (isLogin ? 'login' : 'register'), body);
          API.setAuth(data.access_token, data.user);
          setNav();
          UI.toast('Welcome, ' + data.user.name.split(' ')[0] + '! 🎉');
          location.hash = '#/dashboard';
        } catch (e) { errEl.textContent = e.message; }
        finally { UI.btnLoading(aSubmit, false); }
      });
      ['keydown'].forEach(ev => aSubmit.closest('.auth-card').addEventListener(ev, (e) => { if (e.key === 'Enter') aSubmit.click(); }));
    }

    // create campaign
    const cSubmit = document.getElementById('c-submit');
    if (cSubmit) {
      cSubmit.addEventListener('click', async () => {
        const errEl = document.getElementById('c-err');
        errEl.textContent = '';
        const title = document.getElementById('c-title').value.trim();
        const story = document.getElementById('c-story').value.trim();
        const target = parseInt(document.getElementById('c-target').value, 10);
        const body = {
          title, story,
          category: document.getElementById('c-cat').value,
          city: document.getElementById('c-city').value.trim(),
          hospital: document.getElementById('c-hospital').value.trim(),
          target_amount: target,
        };
        if (title.length < 10) { errEl.textContent = 'Title must be at least 10 characters.'; return; }
        if (story.length < 50) { errEl.textContent = 'Story must be at least 50 characters — details matter for verification.'; return; }
        if (!target || target < 1000) { errEl.textContent = 'Enter a valid goal (min PKR 1,000).'; return; }
        UI.btnLoading(cSubmit, true);
        try {
          const c = await API.post('/campaigns', body);
          UI.toast('Campaign submitted for review ✅');
          location.hash = '#/dashboard';
        } catch (e) { errEl.textContent = e.message; }
        finally { UI.btnLoading(cSubmit, false); }
      });
    }

    // donate modal button
    const btnDonate = document.getElementById('btn-donate');
    if (btnDonate) btnDonate.addEventListener('click', () => openDonateModal(parts[1]));
    const btnCloseCamp = document.getElementById('btn-close-camp');
    if (btnCloseCamp) btnCloseCamp.addEventListener('click', async () => {
      if (!confirm('Close this campaign? Amount collection band ho jayegi. (Owner action)')) return;
      try { await API.post('/campaigns/' + parts[1] + '/close', {}); UI.toast('Campaign closed ✅'); render(); }
      catch (e) { UI.err(e); }
    });
    const btnNewUpdate = document.getElementById('btn-new-update');
    if (btnNewUpdate) btnNewUpdate.addEventListener('click', () => openUpdateModal(parts[1]));

    // dashboard tabs
    document.querySelectorAll('[data-tab]').forEach(t => {
      t.addEventListener('click', () => {
        document.querySelectorAll('[data-tab]').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        document.getElementById('dash-panel-a').classList.toggle('hidden', t.dataset.tab !== 'campaigns');
        document.getElementById('dash-panel-b').classList.toggle('hidden', t.dataset.tab !== 'donations');
      });
    });

    // pledges management
    document.querySelectorAll('[data-pledges]').forEach(b => b.addEventListener('click', () => { location.hash = '#/pledges/' + b.dataset.pledges; }));
    document.querySelectorAll('[data-confirm-don]').forEach(b => b.addEventListener('click', async () => {
      if (!confirm('Bank transfer mil gaya? Amount raised me add hoga aur public ledger pe aayega.')) return;
      UI.btnLoading(b, true);
      try {
        const slug = parts[1];
        const id = b.dataset.confirmDon;
        await API.post('/campaigns/' + slug + '/donations/' + id + '/confirm', {});
        UI.toast('Donation confirmed ✅');
        render();
      } catch (e) { UI.err(e); UI.btnLoading(b, false); }
    }));
    document.querySelectorAll('[data-cancel-don]').forEach(b => b.addEventListener('click', async () => {
      if (!confirm('Cancel this pledge? (Sirf unconfirmed pledges cancel ho sakti hain.)')) return;
      try { await API.post('/donations/' + b.dataset.cancelDon + '/cancel', {}); UI.toast('Pledge cancelled'); render(); }
      catch (e) { UI.err(e); }
    }));

    // admin
    if (base === 'admin') loadAdmin('pending');
  }

  function exploreGo(params) {
    const p = new URLSearchParams();
    if (params.cat) p.set('cat', params.cat);
    if (params.q) p.set('q', params.q);
    if (params.city) p.set('city', params.city);
    if (params.sort && params.sort !== 'recent') p.set('sort', params.sort);
    const q = p.toString();
    const next = '#/explore' + (q ? '?' + q : '');
    if (location.hash === next || (next === '#/explore' && location.hash.replace(/^#\/?/, '').split('?')[0] === 'explore')) render();
    else location.hash = next;
  }

  async function loadAdmin(tab) {
    const panel = document.getElementById('admin-panel');
    if (!panel) return;
    document.querySelectorAll('[data-atab]').forEach(x => x.classList.toggle('active', x.dataset.atab === tab));
    panel.innerHTML = '<div class="loading-row"><div class="spinner"></div></div>';
    try {
      if (tab === 'stats') {
        const s = await API.get('/admin/stats');
        const all = { pending: 0, verified: 0, closed: 0, rejected: 0, ...s.campaigns };
        panel.innerHTML = `<div class="grid">
          ${statCard('Pending review', all.pending, 'pending')}
          ${statCard('Live campaigns', all.verified, 'verified')}
          ${statCard('Closed', all.closed, 'closed')}
          ${statCard('Rejected', all.rejected, 'rejected')}
          ${statCard('Total users', s.users, 'verified')}
          ${statCard('Donations', (s.donations?.confirmed?.count || 0) + ' · PKR ' + UI.fmt(s.donations?.confirmed?.amount || 0).replace('PKR ', ''), 'pending')}
        </div>`;
      } else if (tab === 'users') {
        const users = await API.get('/admin/users');
        panel.innerHTML = users.map(u => `<div class="row-item"><div class="flex-between"><div><div class="r-title">${UI.esc(u.name)} <span class="tag ${u.role === 'admin' ? 'verified' : 'pending'}">${UI.esc(u.role)}</span> ${u.is_suspended ? '<span class="tag rejected">suspended</span>' : ''}</div><div class="r-meta"><span>${UI.esc(u.email)}</span><span>${u.campaigns} campaigns</span><span>${UI.timeAgo(u.created_at)}</span></div></div>${u.role !== 'admin' ? `<button class="btn btn-${u.is_suspended ? 'primary' : 'danger'} btn-sm" data-susp="${u.id}" data-cur="${u.is_suspended ? 'unsuspend' : 'suspend'}">${u.is_suspended ? 'Unsuspend' : 'Suspend'}</button>` : ''}</div></div>`).join('');
        document.querySelectorAll('[data-susp]').forEach(b => b.addEventListener('click', async () => {
          const action = b.dataset.cur;
          if (!confirm('Confirm ' + action + '?')) return;
          try { await API.post('/admin/users/' + b.dataset.susp + '/' + action, {}); UI.toast('User ' + action + 'ed'); loadAdmin('users'); } catch (e) { UI.err(e); }
        }));
      } else {
        const list = await API.get('/admin/campaigns?status_filter=' + tab);
        panel.innerHTML = list.length ? list.map(c => adminCampaignRow(c, tab)).join('') : '<div class="empty"><div class="ico">🗂️</div><h4>Nothing here</h4></div>';
        document.querySelectorAll('[data-verify]').forEach(b => b.addEventListener('click', async () => {
          try { await API.post('/admin/campaigns/' + b.dataset.verify + '/verify', {}); UI.toast('Campaign verified & live ✅'); loadAdmin('pending'); } catch (e) { UI.err(e); }
        }));
        document.querySelectorAll('[data-reject]').forEach(b => b.addEventListener('click', async () => {
          const reason = prompt('Rejection reason (min 10 chars) — owner ko dikhega:');
          if (!reason || reason.trim().length < 10) { UI.toast('Reason required (min 10 chars)', 'err'); return; }
          try { await API.post('/admin/campaigns/' + b.dataset.reject + '/reject', { reason: reason.trim() }); UI.toast('Campaign rejected'); loadAdmin('pending'); } catch (e) { UI.err(e); }
        }));
        document.querySelectorAll('[data-adclose]').forEach(b => b.addEventListener('click', async () => {
          if (!confirm('Close this live campaign?')) return;
          try { await API.post('/admin/campaigns/' + b.dataset.adclose + '/close', {}); UI.toast('Campaign closed'); loadAdmin('live'); } catch (e) { UI.err(e); }
        }));
      }
    } catch (e) { panel.innerHTML = '<div class="empty"><div class="ico">😕</div><h4>Failed to load</h4><p class="small">' + UI.esc(e.message) + '</p></div>'; }
  }

  function statCard(lbl, val, cls) {
    return `<div class="stat-card"><div class="num">${val}</div><div class="lbl ${cls === 'pending' ? 'acc' : ''}">${lbl}</div></div>`;
  }
  function adminCampaignRow(c, tab) {
    const actions = c.status === 'pending'
      ? `<button class="btn btn-primary btn-sm" data-verify="${c.id}">✓ Verify & go live</button><button class="btn btn-danger btn-sm" data-reject="${c.id}">✕ Reject</button>`
      : c.status === 'verified'
        ? `<button class="btn btn-danger btn-sm" data-adclose="${c.id}">Close</button>`
        : '';
    return `<div class="row-item"><div class="r-top"><div><div class="r-title"><a href="#/c/${encodeURIComponent(c.slug)}" target="_blank">${UI.esc(c.title)}</a></div><div class="r-meta"><span>by ${UI.esc(c.owner_name)}</span><span>${UI.esc(c.category)} · ${UI.esc(c.city || '—')}</span><span>${UI.fmt(c.amount_raised)} / ${UI.fmt(c.target_amount)}</span>${UI.statusTag(c.status)}</div></div></div>${actions ? `<div class="r-actions">${actions}</div>` : ''}</div>`;
  }

  function openDonateModal(slug) {
    const presets = [1000, 2500, 5000, 10000];
    UI.openModal(`
      <button class="m-close">×</button>
      <h3>🤲 Make a donation</h3>
      <p class="m-sub">Pledge online — payment campaign owner ke bank account me. Receipt confirm hone par public ledger pe aati hai.</p>
      <div class="don-amount">${presets.map((p, i) => `<button data-preset="${p}" class="${i === 1 ? 'active' : ''}">PKR ${p.toLocaleString()}</button>`).join('')}</div>
      <input class="form-control don-custom" id="don-custom" type="number" min="100" placeholder="Custom amount (PKR)" />
      <div class="form-row"><label>Message (optional)</label><input class="form-control" id="don-msg" maxlength="500" placeholder="Dua ke saath…" /></div>
      <label class="check-row"><input type="checkbox" id="don-anon" /> Hide my name (donate anonymously)</label>
      <div id="don-err" class="form-error"></div>
      <button class="btn btn-primary btn-lg btn-block" id="don-submit">Confirm pledge</button>
      <p class="msg-hint center mt-8">Transfer instructions campaign page par owner ki taraf se milein gi.</p>
    `);
    let sel = 5000;
    document.querySelectorAll('[data-preset]').forEach(b => b.addEventListener('click', () => {
      document.querySelectorAll('[data-preset]').forEach(x => x.classList.remove('active'));
      b.classList.add('active');
      sel = parseInt(b.dataset.preset, 10);
      document.getElementById('don-custom').value = '';
    }));
    document.getElementById('don-custom').addEventListener('input', (e) => {
      sel = 0;
      document.querySelectorAll('[data-preset]').forEach(x => x.classList.remove('active'));
      const v = parseInt(e.target.value, 10);
      if (v > 0) sel = v;
    });
    document.getElementById('don-submit').addEventListener('click', async () => {
      const custom = parseInt(document.getElementById('don-custom').value, 10);
      const amount = custom > 0 ? custom : sel;
      const errEl = document.getElementById('don-err');
      errEl.textContent = '';
      if (!amount || amount < 100) { errEl.textContent = 'Minimum donation PKR 100.'; return; }
      const b = document.getElementById('don-submit');
      UI.btnLoading(b, true);
      try {
        const d = await API.post('/campaigns/' + slug + '/donate', {
          amount, message: document.getElementById('don-msg').value.trim(),
          is_anonymous: document.getElementById('don-anon').checked,
        });
        UI.closeModal();
        UI.toast('Pledge created 🎉 — receipt ref: ' + d.reference);
        render();
      } catch (e) { errEl.textContent = e.message; UI.btnLoading(b, false); }
    });
  }

  function openUpdateModal(slug) {
    UI.openModal(`
      <button class="m-close">×</button>
      <h3>📝 Post an update</h3>
      <p class="m-sub">Donors ko progress batayein — receipts, doctor ka note, shukriya.</p>
      <textarea class="form-control" id="up-body" maxlength="5000" placeholder="e.g. Aaj hospital ne surgery date confirm kar di…"></textarea>
      <div id="up-err" class="form-error"></div>
      <button class="btn btn-primary btn-lg btn-block mt-12" id="up-submit">Post update</button>
    `);
    document.getElementById('up-submit').addEventListener('click', async () => {
      const body = document.getElementById('up-body').value.trim();
      const errEl = document.getElementById('up-err');
      if (body.length < 10) { errEl.textContent = 'Update must be at least 10 characters.'; return; }
      const b = document.getElementById('up-submit');
      UI.btnLoading(b, true);
      try {
        await API.post('/campaigns/' + slug + '/updates', { body });
        UI.closeModal(); UI.toast('Update posted ✅'); render();
      } catch (e) { errEl.textContent = e.message; UI.btnLoading(b, false); }
    });
  }

  function onHash() { render(); }

  function init() {
    setNav();
    navActive();
    // nav clicks
    document.querySelectorAll('[data-nav]').forEach(a => a.addEventListener('click', (e) => {
      const nav = a.dataset.nav;
      if (nav === 'logout') return;
      if (nav === 'home') { location.hash = ''; return; }
      location.hash = '#/' + nav;
      document.querySelectorAll('.nav-links, .topbar-actions').forEach(x => x.classList.remove('open'));
    }));
    const logout = document.getElementById('btn-logout');
    if (logout) logout.addEventListener('click', () => { API.clearAuth(); setNav(); UI.toast('Logged out. Khuda hafiz! 👋'); location.hash = ''; render(); });
    const ham = document.getElementById('hamburger');
    if (ham) ham.addEventListener('click', () => {
      document.querySelectorAll('.nav-links, .topbar-actions').forEach(x => x.classList.toggle('open'));
    });
    window.addEventListener('hashchange', onHash);
    render();
  }

  return { init, setNav };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
