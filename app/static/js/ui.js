/* Madad — shared UI helpers */
const UI = (() => {
  const fmt = (n) => 'PKR ' + Number(n || 0).toLocaleString('en-PK');
  const esc = (s) => {
    return String(s ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  };
  const timeAgo = (iso) => {
    if (!iso) return '';
    const diff = (Date.now() - new Date(iso).getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 86400 * 30) return Math.floor(diff / 86400) + 'd ago';
    return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
  };
  const dateTime = (iso) => new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });

  function toast(msg, type) {
    const el = document.getElementById('toast');
    if (!el) return;
    el.textContent = msg;
    el.className = 'toast show ' + (type || 'ok');
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.className = 'toast'; }, 3200);
  }
  function err(e) { toast(e.message || 'Something went wrong.', 'err'); }

  function initButtons() {
    document.querySelectorAll('button.btn-loading-ready').forEach(() => {});
  }

  function btnLoading(b, on) {
    if (!b) return;
    if (on) { b.classList.add('btn-loading'); b.disabled = true; }
    else { b.classList.remove('btn-loading'); b.disabled = false; }
  }

  function statusTag(s) {
    const map = { pending: 'pending', verified: 'live', closed: 'closed', rejected: 'rejected' };
    const cls = map[s] || 'verified';
    return '<span class="tag ' + cls + '">' + esc(s) + '</span>';
  }
  function donStatusTag(s) {
    const map = { pledged: 'pledged', confirmed: 'confirmed', cancelled: 'cancelled' };
    return '<span class="tag ' + (map[s] || 'pledged') + '">' + esc(s) + '</span>';
  }
  function categoryClass(cat) { return 'cat-' + (cat || 'other'); }

  function openModal(html) {
    const root = document.getElementById('modal-root');
    root.innerHTML = '<div class="modal-backdrop"><div class="modal">' + html + '</div></div>';
    root.querySelector('.modal-backdrop').addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-backdrop')) closeModal();
    });
    const closeBtn = root.querySelector('.m-close');
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
  }
  function closeModal() { document.getElementById('modal-root').innerHTML = ''; }

  return { fmt, esc, timeAgo, dateTime, toast, err, btnLoading, statusTag, donStatusTag, categoryClass, openModal, closeModal };
})();
