/* Madad — tiny API client with auth + error normalization */
const API = (() => {
  const TOKEN_KEY = 'madad_token';
  const USER_KEY = 'madad_user';

  function token() { return localStorage.getItem(TOKEN_KEY) || ''; }
  function user() {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); }
    catch { return null; }
  }
  function setAuth(tok, u) {
    localStorage.setItem(TOKEN_KEY, tok);
    localStorage.setItem(USER_KEY, JSON.stringify(u));
  }
  function clearAuth() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY); }
  function isAuthed() { return !!token(); }

  async function request(method, path, body) {
    const headers = { 'Content-Type': 'application/json' };
    const t = token();
    if (t) headers['Authorization'] = 'Bearer ' + t;
    let res;
    try {
      res = await fetch('/api' + path, {
        method, headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (err) {
      throw new Error('Network error — check your connection and try again.');
    }
    let data = null;
    try { data = await res.json(); } catch { /* non-json */ }
    if (!res.ok) {
      let msg = 'Something went wrong (HTTP ' + res.status + ').';
      if (data && data.detail) {
        msg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }
      const e = new Error(msg);
      e.status = res.status;
      throw e;
    }
    return data;
  }

  return {
    token, user, setAuth, clearAuth, isAuthed, request,
    get: (p) => request('GET', p),
    post: (p, b) => request('POST', p, b),
  };
})();
