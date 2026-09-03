/* Madad — page views. Each render fn returns HTML (or mounts its own listeners). */

async function vHome() {
  const [stats, campaigns] = await Promise.all([
    API.get('/public/stats'),
    API.get('/campaigns?limit=6'),
  ]);
  const cats = [
    ['cancer', '🎗️ Cancer'], ['surgery', '🩺 Surgery'], ['child-health', '🧒 Child Health'],
    ['thalassemia', '🩸 Thalassemia'], ['dialysis', '💧 Dialysis'], ['accident', '🚑 Accident'],
    ['maternity', '🤱 Maternity'], ['cardiac', '❤️ Cardiac'], ['other', '🤲 Other'],
  ];
  return `
    <section class="hero">
      <span class="eyebrow">🇵🇰 Verified medical crowdfunding for Pakistan</span>
      <h1>Jab ilaaj ka khwab <span class="grad">logon ke dilon</span> se milta hai</h1>
      <p class="sub">Madad par har campaign document-verify hota hai, har donation ek public ledger pe hoti hai — har rupee ka hisaab. Ilaaj ke liye madad mangna ab be-ghairat nahi, behtareen amal hai.</p>
      <div class="hero-ctas">
        <a href="#" class="btn btn-primary btn-lg" data-nav="explore">Explore campaigns</a>
        <a href="#" class="btn btn-ghost btn-lg ${API.isAuthed() ? '' : 'hidden'}" data-nav="dashboard">Start a campaign</a>
        <a href="#" class="btn btn-ghost btn-lg ${API.isAuthed() ? 'hidden' : ''}" data-nav="register">Register free</a>
      </div>
    </section>

    <section class="stats-strip">
      <div class="stat-card"><div class="num">${UI.fmt(stats.total_raised || 0)}</div><div class="lbl acc">raised & verified</div></div>
      <div class="stat-card"><div class="num">${(stats.verified_campaigns || 0).toLocaleString()}</div><div class="lbl">live campaigns</div></div>
      <div class="stat-card"><div class="num">${(stats.total_donations || 0).toLocaleString()}</div><div class="lbl">donations</div></div>
      <div class="stat-card"><div class="num">${(stats.cities || 0).toLocaleString()}</div><div class="lbl">cities</div></div>
    </section>

    <div class="sec"><h2>🩷 Recent campaigns</h2><a href="#" data-nav="explore" class="more">See all →</a></div>
    ${campaignCards(campaigns)}

    <div class="sec"><h2>🏷️ Browse by category</h2></div>
    <div class="chip-row">${cats.map(([v, l]) => `<a href="#" class="chip" data-nav="explore" data-cat="${v}">${l}</a>`).join('')}</div>

    <div class="sec"><h2>🔍 How Madad works</h2></div>
    <div class="grid">
      ${howCard('1', '📄', 'Campaign submit karo', 'Apni medical zaroorat, hospital estimate aur documents ke saath campaign banayein.')}
      ${howCard('2', '🛡️', 'Team verify karti hai', 'Har campaign documents ke saath verify hota hai — sirf asli aur zaroori campaigns live hote hain.')}
      ${howCard('3', '🤲', 'Log donate karte hain', 'Donors online pledge karte hain, amount seedha campaign owner ke verified bank account me jaata hai.')}
      ${howCard('4', '📒', 'Har rupee ka hisaab', 'Public ledger par har donation, har update — goal poora hote hi campaign band, hisaab saaf.')}
    </div>
    <div class="footer">Made with <span class="f-heart">♥</span> for Pakistan · Madad v1.0.0</div>
  `;
}

function howCard(n, ico, t, d) {
  return `<div class="card"><div class="card-head cat-other" style="justify-content:center;align-items:flex-start;gap:6px;"><span style="font-size:26px;">${ico}</span><div><div style="font-size:12px;font-weight:700;color:rgba(255,255,255,.75);">STEP ${n}</div><h3 style="margin-top:0;">${UI.esc(t)}</h3></div></div><div class="card-body"><p class="muted small">${UI.esc(d)}</p></div></div>`;
}

async function vExplore(params = {}) {
  const cat = params.cat || '';
  const city = params.city || '';
  const q = params.q || '';
  const sort = params.sort || 'recent';
  const qs = new URLSearchParams();
  if (cat) qs.set('category', cat);
  if (city) qs.set('city', city);
  if (q) qs.set('q', q);
  qs.set('sort', sort);
  qs.set('limit', '24');
  const campaigns = await API.get('/campaigns?' + qs.toString());
  const cats = [
    ['', 'All'], ['cancer', 'Cancer'], ['surgery', 'Surgery'], ['child-health', 'Child Health'],
    ['thalassemia', 'Thalassemia'], ['dialysis', 'Dialysis'], ['accident', 'Accident'],
    ['maternity', 'Maternity'], ['cardiac', 'Cardiac'], ['other', 'Other'],
  ];
  return `
    <div class="sec" style="margin-top:30px;"><h1 style="font-family:var(--font-display);font-size:28px;font-weight:800;">Explore campaigns</h1></div>
    <div class="chip-row" style="margin-bottom:6px;">
      ${cats.map(([v, l]) => `<button class="chip ${v === cat ? 'active' : ''}" data-cat-btn="${v}">${l}</button>`).join('')}
    </div>
    <div class="filterbar">
      <div class="searchbox"><span class="s-ico">🔍</span><input class="form-control" id="f-search" placeholder="Search title or story…" value="${UI.esc(q)}" /></div>
      <input class="form-control" id="f-city" style="max-width:170px;" placeholder="City" value="${UI.esc(city)}" />
      <select class="form-control" id="f-sort" style="max-width:150px;">
        <option value="recent" ${sort === 'recent' ? 'selected' : ''}>Newest</option>
        <option value="urgent" ${sort === 'urgent' ? 'selected' : ''}>Most urgent</option>
        <option value="raised" ${sort === 'raised' ? 'selected' : ''}>Most raised</option>
      </select>
      <button class="btn btn-ghost btn-sm" id="f-apply">Filter</button>
    </div>
    ${campaignCards(campaigns)}
    <div class="footer">Madad v1.0.0 · sirf verified campaigns public hain</div>
  `;
}

async function vCampaign(slug) {
  const [c, updates, ledger] = await Promise.all([
    API.get('/campaigns/' + slug),
    API.get('/campaigns/' + slug + '/updates'),
    API.get('/campaigns/' + slug + '/donations'),
  ]);
  const done = c.amount_raised >= c.target_amount;
  const isOwner = API.user() && API.user().id === c.owner_id;
  const confirmed = ledger.filter(d => d.status === 'confirmed');
  const donationsRows = confirmed.length
    ? confirmed.slice(0, 20).map(d => ledgerRow(d)).join('')
    : '<div class="empty" style="padding:24px;"><div class="ico">🕊️</div><h4>No donations yet</h4><p class="small">Be the first to help this family.</p></div>';
  const updatesHtml = updates.length
    ? updates.map(u => `<div class="update-item"><div class="u-meta"><span><strong>${UI.esc(u.author_name)}</strong></span><span>${UI.dateTime(u.created_at)}</span></div><div>${UI.esc(u.body)}</div></div>`).join('')
    : '<p class="muted small">No updates posted yet.</p>';
  const shareUrl = location.origin + '/#/c/' + c.slug;
  return `
    <div class="detail-grid">
      <div class="detail-main">
        <div class="d-cat">${UI.esc(c.category)} · ${UI.esc(c.city || 'Pakistan')}${c.hospital ? ' · ' + UI.esc(c.hospital) : ''}</div>
        <h1>${UI.esc(c.title)}</h1>
        <div class="d-owner"><span class="avatar">${UI.esc((c.owner_name || '?').slice(0, 1))}</span><span>by <strong>${UI.esc(c.owner_name)}</strong></span><span class="tag ${done ? 'done2' : 'live'}">${done ? 'goal reached 🎉' : 'verified · live'}</span><span class="muted small">${UI.timeAgo(c.created_at)}</span></div>
        <div class="d-story"><h3>The story</h3>${UI.esc(c.story)}${c.hospital ? `<div class="d-hospital">🏥 <span><strong>Hospital:</strong> ${UI.esc(c.hospital)}</span></div>` : ''}</div>
        <div class="updates"><h3 style="font-family:var(--font-display);font-size:18px;margin-bottom:12px;">📝 Updates</h3>${updatesHtml}${isOwner && !done ? `<button class="btn btn-ghost btn-sm mt-12" id="btn-new-update">+ Post an update</button>` : ''}</div>
      </div>
      <div class="donate-card">
        <div class="panel">
          <div class="flex-between"><h3>Donation goal</h3><span class="${done ? 'pct-big done' : 'pct-big'}">${c.progress_percent}%</span></div>
          <div class="goal-line ${done ? 'done' : ''}"><div style="width:${Math.min(100, c.progress_percent)}%"></div></div>
          <div class="meta-line"><span><strong>${UI.fmt(c.amount_raised)}</strong> raised</span><span>of ${UI.fmt(c.target_amount)}</span></div>
          <div class="meta-line"><span>${(c.donor_count || 0)} donors</span><span>${UI.fmt(c.target_amount - c.amount_raised)} remaining</span></div>
          ${done
            ? `<button class="btn btn-accent btn-block btn-lg mt-12" disabled>🎉 Goal reached — campaign closed</button>`
            : API.isAuthed()
              ? (isOwner
                ? `<button class="btn btn-ghost btn-block mt-12" disabled>You own this campaign</button><button class="btn btn-danger btn-block btn-sm mt-8" id="btn-close-camp">Close campaign</button>`
                : `<button class="btn btn-primary btn-lg btn-block mt-12" id="btn-donate">🤲 Donate now</button>`)
              : `<button class="btn btn-primary btn-lg btn-block mt-12" data-nav="login">Log in to donate</button>`
          }
          <p class="msg-hint mt-8">Pledge online, phir payment campaign owner ke verified bank account me. Owner receipt confirm karta hai — har donation public ledger pe aati hai.</p>
        </div>
        <div class="panel mt-12">
          <h3>📒 Public ledger</h3>
          ${donationsRows}
        </div>
        <div class="panel mt-12">
          <h3>🔗 Share</h3>
          <p class="msg-hint">Copy this link and share it on WhatsApp, Instagram or Facebook:</p>
          <input class="form-control mono mt-8" value="${UI.esc(shareUrl)}" readonly onclick="this.select()" />
        </div>
      </div>
    </div>
  `;
}

function ledgerRow(d) {
  const who = d.is_anonymous
    ? '<span class="avatar">🙈</span><span class="nm">Anonymous</span>'
    : `<span class="avatar">${UI.esc((d.donor_name || '?').slice(0, 1))}</span><span class="nm">${UI.esc(d.donor_name || 'Donor')}</span>`;
  return `<div class="ledger-item"><div class="who">${who}<div><div class="ref">${UI.esc(d.reference)} · ${UI.timeAgo(d.created_at)}</div>${d.message ? `<div class="msg">“${UI.esc(d.message)}”</div>` : ''}</div></div><span class="amt">${UI.fmt(d.amount)}</span></div>`;
}

function campaignCards(list) {
  if (!list || !list.length) return '<div class="empty"><div class="ico">🕊️</div><h4>No campaigns found</h4><p>Try a different filter or search.</p></div>';
  return `<div class="grid">${list.map(c => `
    <a class="card" href="#/c/${encodeURIComponent(c.slug)}">
      <div class="card-head ${UI.categoryClass(c.category)}">
        <span class="cat">${UI.esc(c.category)} ${c.city ? '· ' + UI.esc(c.city) : ''}</span>
        <h3>${UI.esc(c.title)}</h3>
      </div>
      <div class="card-body">
        <div class="progress ${c.amount_raised >= c.target_amount ? 'done' : ''}"><div style="width:${Math.min(100, c.progress_percent)}%"></div></div>
        <div class="card-meta">
          <span class="raised">${UI.fmt(c.amount_raised)} <small>of ${UI.fmt(c.target_amount)}</small></span>
          <span class="pct ${c.amount_raised >= c.target_amount ? 'done' : ''}">${c.progress_percent}%</span>
        </div>
        <div class="card-foot">
          <span class="who"><span class="avatar">${UI.esc((c.owner_name || '?').slice(0, 1))}</span><span>${UI.esc(c.owner_name)}</span></span>
          <span>${c.donor_count || 0} donors</span>
        </div>
      </div>
    </a>`).join('')}</div>`;
}

async function vLogin() {
  return authShell('login');
}
async function vRegister() {
  return authShell('register');
}
function authShell(mode) {
  const isLogin = mode === 'login';
  return `
    <div class="auth-wrap">
      <div class="auth-card">
        <h2>${isLogin ? 'Welcome back 👋' : 'Create your account'}</h2>
        <p class="hint">${isLogin ? 'Log in to donate or manage your campaigns.' : 'Free forever for donors. Campaign owners verify once, then raise.'}</p>
        ${!isLogin ? `<div class="form-row"><label>Full name <span class="req">*</span></label><input class="form-control" id="a-name" placeholder="e.g. Ayesha Khan" autocomplete="name" /></div>` : ''}
        <div class="form-row"><label>Email <span class="req">*</span></label><input class="form-control" id="a-email" type="email" placeholder="you@example.com" autocomplete="email" /></div>
        <div class="form-row"><label>Password <span class="req">*</span></label><input class="form-control" id="a-pass" type="password" placeholder="${isLogin ? 'Your password' : 'Min 8 characters'}" autocomplete="${isLogin ? 'current-password' : 'new-password'}" /></div>
        <div id="a-err" class="form-error"></div>
        <button class="btn btn-primary btn-lg btn-block" id="a-submit">${isLogin ? 'Log in' : 'Create account'}</button>
        <p class="auth-switch">${isLogin ? 'No account yet? <a href="#/register">Sign up free</a>' : 'Already have one? <a href="#/login">Log in</a>'}</p>
        <p class="msg-hint center">Demo: admin@madad.pk / admin12345 · donor@example.com / demo12345</p>
      </div>
    </div>
  `;
}

async function vDashboard() {
  const me = API.user();
  if (!me) return '<div class="empty"><div class="ico">🔒</div><h4>Log in first</h4></div>';
  const [mine, myDons] = await Promise.all([API.get('/my/campaigns'), API.get('/my/donations')]);
  const tabs = `
    <div class="tabs">
      <button class="tab active" data-tab="campaigns">My campaigns (${mine.length})</button>
      <button class="tab" data-tab="donations">My donations (${myDons.length})</button>
    </div>
  `;
  const panelA = mine.length ? mine.map(c => myCampaignRow(c)).join('') : `<div class="empty"><div class="ico">🩺</div><h4>No campaigns yet</h4><p>Start your first verified medical campaign.</p></div>`;
  const panelB = myDons.length ? myDons.map(d => donationRow(d)).join('') : `<div class="empty"><div class="ico">🤲</div><h4>No donations yet</h4><p>Donations you make will appear here with receipts.</p></div>`;
  return `
    <div class="dash-head"><h1>Salaam, ${UI.esc(me.name.split(' ')[0])} 👋</h1><a href="#/campaign/new" class="btn btn-primary">+ Start a campaign</a></div>
    ${tabs}
    <div id="dash-panel-a">${panelA}</div>
    <div id="dash-panel-b" class="hidden">${panelB}</div>
  `;
}

function myCampaignRow(c) {
  const pendingNote = c.status === 'pending' ? '<div class="status-note">⏳ <strong>Pending review</strong> — hamari team documents verify kar rahi hai. Verification ke baad yeh public ho jayega.</div>' : '';
  const rejectedNote = c.status === 'rejected' ? `<div class="status-note">❌ <strong>Rejected:</strong> ${UI.esc(c.reject_reason || 'reason not given')}</div>` : '';
  const closedNote = c.status === 'closed' ? '<div class="status-note">✅ Campaign closed — shukriya. Hisaab public ledger par hai.</div>' : '';
  return `
    <div class="row-item">
      ${pendingNote}${rejectedNote}${closedNote}
      <div class="r-top"><div><div class="r-title"><a href="#/c/${encodeURIComponent(c.slug)}">${UI.esc(c.title)}</a></div>
      <div class="r-meta"><span>${UI.fmt(c.amount_raised)} / ${UI.fmt(c.target_amount)} (${c.progress_percent}%)</span><span>${c.donor_count} donors</span><span>${UI.statusTag(c.status)}</span></div></div></div>
      <div class="progress ${c.amount_raised >= c.target_amount ? 'done' : ''}" style="margin-top:10px;"><div style="width:${Math.min(100, c.progress_percent)}%"></div></div>
      ${c.status === 'verified' && c.amount_raised < c.target_amount ? `<div class="r-actions"><a class="btn btn-ghost btn-sm" href="#/c/${encodeURIComponent(c.slug)}">View</a><button class="btn btn-ghost btn-sm" data-pledges="${c.slug}">Manage pledges</button></div>` : ''}
    </div>
  `;
}

function donationRow(d) {
  const cancelBtn = d.status === 'pledged'
    ? `<button class="btn btn-outline-danger btn-sm" data-cancel-don="${d.id}">Cancel pledge</button>`
    : '';
  return `
    <div class="row-item"><div class="flex-between">
      <div><div class="r-title">${UI.fmt(d.amount)} <span class="muted small">→</span> <a href="#/c/${encodeURIComponent(d.campaign_slug)}">${UI.esc(d.campaign_title)}</a></div>
      <div class="r-meta"><span class="mono">${UI.esc(d.reference)}</span><span>${UI.dateTime(d.created_at)}</span>${UI.donStatusTag(d.status)}</div>
      ${d.status === 'confirmed' ? `<p class="msg-hint mt-8">✅ Owner ne receipt confirm kar di — yeh amount public ledger pe registered hai. Receipt: <span class="mono">${UI.esc(d.reference)}</span></p>` : ''}
      </div>${cancelBtn}</div>
    </div>
  `;
}

async function vNewCampaign() {
  const cats = [['cancer', 'Cancer'], ['surgery', 'Surgery'], ['child-health', 'Child Health'], ['thalassemia', 'Thalassemia'], ['dialysis', 'Dialysis'], ['accident', 'Accident'], ['maternity', 'Maternity'], ['cardiac', 'Cardiac'], ['other', 'Other']];
  return `
    <div class="auth-wrap"><div class="auth-card">
      <h2>Start a campaign 🩺</h2>
      <p class="hint">Documentation submit karne ke baad hamari team 24–48 ghanton me verify karti hai. <strong>Zaroori:</strong> sirf asli medical campaigns — hospital estimate ya doctor ke naam ke baghair campaign reject ho jata hai.</p>
      <div class="form-row"><label>Campaign title <span class="req">*</span></label><input class="form-control" id="c-title" maxlength="150" placeholder="e.g. Surgery for my mother at JPMC" /><div class="form-note">10–150 characters. Patient ka naam aur treatment clearly likhein.</div></div>
      <div class="form-row"><label>Category <span class="req">*</span></label>
        <select class="form-control" id="c-cat">${cats.map(([v, l]) => `<option value="${v}">${l}</option>`).join('')}</select></div>
      <div class="form-row"><label>Goal amount (PKR) <span class="req">*</span></label><input class="form-control" id="c-target" type="number" min="1000" max="100000000" placeholder="e.g. 1500000" /><div class="form-note">Hospital estimate ke mutabiq. Over-target donations block ho jati hain.</div></div>
      <div class="form-row"><label>City</label><input class="form-control" id="c-city" maxlength="80" placeholder="e.g. Karachi" /></div>
      <div class="form-row"><label>Hospital</label><input class="form-control" id="c-hospital" maxlength="150" placeholder="e.g. Jinnah Hospital, Lahore" /></div>
      <div class="form-row"><label>The story <span class="req">*</span></label><textarea class="form-control" id="c-story" maxlength="10000" placeholder="Patient ka background, diagnosis, treatment plan aur financial zaroorat — sach aur detail me likhein. (min 50 characters)"></textarea></div>
      <div id="c-err" class="form-error"></div>
      <button class="btn btn-primary btn-lg btn-block" id="c-submit">Submit for verification</button>
      <p class="msg-hint center mt-12">Submit karne ke baad campaign review queue me jaata hai — dashboard me status track karo.</p>
    </div></div>
  `;
}

async function vAdmin() {
  const me = API.user();
  if (!me || me.role !== 'admin') return '<div class="empty"><div class="ico">⛔</div><h4>Admins only</h4></div>';
  const tabs = `<div class="tabs"><button class="tab active" data-atab="pending">Pending review</button><button class="tab" data-atab="live">Live</button><button class="tab" data-atab="users">Users</button><button class="tab" data-atab="stats">Stats</button></div>`;
  return `<div class="dash-head"><h1>🛡️ Admin panel</h1></div>${tabs}<div id="admin-panel"><div class="loading-row"><div class="spinner"></div></div></div>`;
}

async function vPledges(slug) {
  const pledges = await API.get('/my/campaigns/' + slug + '/pledges');
  const rows = pledges.length ? pledges.map(p => `
    <div class="row-item"><div class="flex-between">
      <div><div class="r-title">${p.is_anonymous ? '🙈 Anonymous donor' : UI.esc(p.donor_name || 'Donor')} — ${UI.fmt(p.amount)}</div>
      <div class="r-meta"><span class="mono">${UI.esc(p.reference)}</span><span>${UI.dateTime(p.created_at)}</span>${UI.donStatusTag(p.status)}</div>
      ${p.message ? `<p class="small muted mt-8">“${UI.esc(p.message)}”</p>` : ''}
      <p class="msg-hint mt-8">Donor ko batao: bank account transfer ke baad yahan <strong>Confirm receipt</strong> dabao — amount raised me add hoga aur public ledger pe aayega.</p>
      </div>${p.status === 'pledged' ? `<button class="btn btn-primary btn-sm" data-confirm-don="${p.id}">✓ Confirm receipt</button>` : ''}</div>
    </div>`).join('')
    : '<div class="empty"><div class="ico">🕊️</div><h4>No pledges yet</h4><p>Jab donors pledge karein ge, woh yahan confirm karne ke liye aayein gi.</p></div>';
  return `<div class="dash-head"><h1>💳 Manage pledges</h1><a href="#/dashboard" class="btn btn-ghost btn-sm">← Back</a></div><div class="mt-20">${rows}</div>`;
}
