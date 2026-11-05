window.ProfRatesAPI = Object.freeze({
 async response(path, options={}) {
  if (!path.startsWith('/api/')) throw new Error('Invalid API URL');
  const en = document.documentElement.lang.startsWith('en'), url = new URL(path, location.origin);
  if (/^\/api\/(lecturers(?:\/\d+)?|rankings|academic\/chairs)$/.test(url.pathname)) url.searchParams.set('lang', en ? 'en' : 'hy');
  if (['/api/admin/users','/api/admin/dashboard','/api/admin/student-roster'].includes(url.pathname)) url.searchParams.set('lang',en?'en':'hy');
  const auth = await window.ProfRatesAuth?.getHeaders?.() || {};
  const csrf = document.cookie.split('; ').find(part => part.startsWith('pr_csrf='))?.split('=')[1];
  auth['X-ProfRates-Request'] = '1';
  if (csrf) auth['X-CSRF-Token'] = decodeURIComponent(csrf);
  const response = await fetch(url.pathname + url.search, {...options, credentials:'same-origin', headers:{Accept:'application/json', ...auth, ...options.headers}});
  if (!response.ok) {
   const body = await response.json().catch(() => null), detail = body?.detail;
   let message;
   if (detail && !Array.isArray(detail) && typeof detail === 'object') message = detail[en ? 'en' : 'hy'];
   if (Array.isArray(detail)) message = detail.map(item => item.msg).join('; ');
   if (!message) message = typeof detail === 'string' ? (window.ProfRatesI18n?.error(detail, response.status) || detail) : (en ? 'The request failed. Please try again.' : 'Հարցումը չհաջողվեց։ Փորձեք կրկին։');
   const error = new Error(message); error.status = response.status; throw error;
  }
  return response;
 },
 async request(path, options={}) { const response = await this.response(path, options); return response.status === 204 ? null : response.json(); },
 async save(path, method, body) { return this.request(path, {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)}); },
 async download(path, filename) {
  const response = await this.response(path), url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = filename; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
 }
});
