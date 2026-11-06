(() => {
  const {text, safeNext} = ProfRatesSession;
  const container = document.querySelector('.form-container .form');
  const button = container.querySelector('.submit');
  const email = container.querySelector('.mail'), password = container.querySelector('.pass');
  const toggle=container.querySelector('.password-toggle');
  if(toggle){
    toggle.addEventListener('keydown',event=>event.stopPropagation());
    toggle.onclick=()=>{
      const visible=password.type==='password',start=password.selectionStart,end=password.selectionEnd;
      password.type=visible?'text':'password';toggle.setAttribute('aria-pressed',String(visible));
      toggle.setAttribute('aria-label',visible?text('Թաքցնել գաղտնաբառը','Hide password'):text('Ցույց տալ գաղտնաբառը','Show password'));
      toggle.querySelector('.eye-slash').style.display=visible?'':'none';
      password.focus();if(start!==null)password.setSelectionRange(start,end);
    };
  }
  const fields = [email, password];
  for (const error of container.querySelectorAll('.error-message')) error.remove();
  for (const input of fields) {
    input.required = true; input.setAttribute('aria-required', 'true');
    if (!input.id) input.id = 'auth-' + (input === email ? 'email' : 'password');
    const hasLabel = Array.from(container.querySelectorAll('label')).some(label => label.htmlFor === input.id);
    if (!hasLabel && !input.getAttribute('aria-label')) input.setAttribute('aria-label', input.placeholder || text('Ամբիոն', 'Chair'));
    input.addEventListener('input', () => clear(input));
    input.addEventListener('change', () => clear(input));
  }
  email.maxLength=255;password.maxLength=128;
  email.autocomplete = 'username'; password.autocomplete = 'current-password';
  const status = document.createElement('p'); status.setAttribute('role', 'alert'); status.className = 'pr-form-status'; button.before(status);
  function clear(input) {
    document.getElementById(input.id + '-validation')?.remove(); input.removeAttribute('aria-invalid'); input.removeAttribute('aria-describedby');
  }
  function error(input, message) {
    clear(input); const note = document.createElement('p'); note.id = input.id + '-validation';
    note.className = 'error-message show'; note.textContent = message;
    const label = input.closest('.auth-name-field')?.querySelector('label');
    if (label) label.after(note); else (input.closest('.auth-password')||input).after(note);
    input.setAttribute('aria-invalid', 'true'); input.setAttribute('aria-describedby', note.id);
  }
  async function submit(event) {
    if (button.disabled) {event.preventDefault();return;}
    event.preventDefault(); fields.forEach(clear); status.textContent = ''; let valid = true;
    for (const input of fields) if (!input.disabled && !input.value.trim()) {
      error(input, text('Այս դաշտը պարտադիր է։', 'This field is required.')); valid = false;
    }
    if (email.value.trim() && (!email.validity.valid || !/^[^\s@]+@polytechnic\.am$/i.test(email.value.trim()))) {
      error(email, text('Մուտքագրեք համալսարանական էլ․ հասցե՝ example@polytechnic.am։', 'Use a university email such as example@polytechnic.am.')); valid = false;
    }
    if (!valid) { container.querySelector('[aria-invalid="true"]')?.focus(); return; }
    button.disabled = true;
    try {
      await ProfRatesAPI.save('/api/auth/login', 'POST', {
        Email:email.value.trim(),Password:password.value,
        RememberMe:Boolean(container.querySelector('.check')?.checked)
      });
      const state=await ProfRatesSession.check();
      if(!state.authenticated)throw new Error(text('Մուտքը սերվերում չի հաստատվել։','The server has not verified this sign-in.'));
      location.href=safeNext(new URLSearchParams(location.search).get('next'));
    } catch (e) {
      status.textContent=e.message;
    }
    finally { button.disabled = false; }
  }
  button.onclick = submit;
  container.addEventListener('keydown', event => { if (event.key === 'Enter') submit(event); });
  const next = new URLSearchParams(location.search).get('next');
  if (next) for (const link of document.querySelectorAll('a[href*="login_"]')) link.search = '?next=' + encodeURIComponent(safeNext(next));
})();
