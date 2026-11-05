/* Student access comes from the server, never from localStorage or page names. */
window.ProfRatesSession = (() => {
  const en = document.documentElement.lang.startsWith('en');
  const text = (hy, english) => en ? english : hy;
  let current = null;
  const accountPage = type => `${type}_${en ? 'eng' : 'arm'}.html`;
  function safeNext(value) {
    if (!value) return '/frontend/' + accountPage('home');
    let url;
    try { url = new URL(value, location.href); } catch { return '/frontend/' + accountPage('home'); }
    return url.origin === location.origin && url.pathname.startsWith('/frontend/')
      ? url.pathname + url.search : '/frontend/' + accountPage('home');
  }
  function dialog(message, next = location.href, account = true) {
    document.getElementById('prDialog')?.remove();
    const modal = document.createElement('dialog'); modal.id = 'prDialog'; modal.className = 'pr-dialog';
    const title = document.createElement('h2'); title.textContent = text('ProfRates', 'ProfRates');
    const note = document.createElement('p'); note.textContent = message;
    const actions = document.createElement('div'); actions.className = 'pr-dialog-actions';
    if (account) for (const [type, label] of [['login', text('Մուտք', 'Sign in')], ['sign_up', text('Գրանցվել', 'Register')]]) {
      const link = document.createElement('a'); link.className = 'pr-button'; link.textContent = label;
      link.href = accountPage(type) + '?next=' + encodeURIComponent(safeNext(next)); actions.append(link);
    }
    const close = document.createElement('button'); close.type = 'button'; close.className = 'pr-button pr-secondary';
    close.textContent = text('Փակել', 'Close'); close.onclick = () => modal.close(); actions.append(close);
    modal.append(title, note, actions); modal.setAttribute('aria-label', 'ProfRates');
    document.body.append(modal); modal.addEventListener('close', () => modal.remove()); modal.showModal();
    return modal;
  }
  async function check() {
    try { current = await ProfRatesAPI.request('/api/auth/session'); }
    catch (error) {
      current = {authenticated: false, error: error.status === 401 ? null : error};
    }
    updateNavigation(); return current;
  }
  function updateNavigation() {
    if (current?.authenticated && document.querySelector('.right-nav') && !document.querySelector('.my-rates-btn')) {
      const link=document.createElement('a');link.className='my-rates-btn';link.href=accountPage('ratings');link.textContent=text('Իմ գնահատականները','My ratings');document.querySelector('.right-nav').prepend(link);
    }
    for (const link of document.querySelectorAll('a[href*="ratings_arm.html"],a[href*="ratings_eng.html"]')) {
      link.hidden = !current?.authenticated;
    }
    for (const link of document.querySelectorAll('.logout-btn, .right-nav .login-btn')) {
      if (!current?.authenticated) {
        link.onclick = null;
        link.textContent = text('Մուտք', 'Sign in'); link.href = accountPage('login');
      } else {
        link.textContent = text('Ելք', 'Logout'); link.href = '#';
        link.onclick=async event=>{event.preventDefault();try{await ProfRatesAPI.save('/api/auth/logout','POST',{});location.href=text('home_arm_guest.html','home_eng_guest.html');}catch(error){dialog(error.message,location.href,false);}};
      }
    }
  }
  async function requireStudent(next = location.href) {
    const state = await check();
    if (state.authenticated && state.role === 'student') return true;
    dialog(state.error?.message || text('Գնահատելու համար մուտք գործեք կամ գրանցվեք։', 'Sign in or register to rate a lecturer.'), next);
    return false;
  }
  document.addEventListener('click', async event => {
    const link = event.target.closest('a[href]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    const url = new URL(link.href, location.href);
    if (url.origin === location.origin && /\/(rate|ratings)_(arm|eng)\.html$/.test(url.pathname)) {
      event.preventDefault(); if (await requireStudent(url.href)) location.href = url.href;
    }
  });
  const ready = check();
  if (/\/rate_(arm|eng)\.html$/.test(location.pathname)) {
    for(const link of document.querySelectorAll('a[href*="rate_arm.html"],a[href*="rate_eng.html"]')) link.search=location.search;
  }
  return {ready, check, requireStudent, dialog, safeNext, text};
})();
