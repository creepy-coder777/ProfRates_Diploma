(() => {
  const {text, dialog, safeNext} = ProfRatesSession;
  const register = location.pathname.includes('sign_up');
  const container = document.querySelector('.form-container .form');
  const button = container.querySelector('.submit');
  const email = container.querySelector('.mail'), password = container.querySelector('.pass');
  const first = container.querySelector('.fname'), last = container.querySelector('.lname');
  const chair = register ? container.querySelector('#menu') : null;
  const group = register ? container.querySelector('#auth-group') : null;
  const fields = [email, password];
  for (const error of container.querySelectorAll('.error-message')) error.remove();
  for (const input of fields) {
    input.required = true; input.setAttribute('aria-required', 'true');
    if (!input.id) input.id = 'auth-' + (input === email ? 'email' : input === first ? 'first-name' : input === last ? 'last-name' : input === chair ? 'chair' : 'password');
    const hasLabel = Array.from(container.querySelectorAll('label')).some(label => label.htmlFor === input.id);
    if (!hasLabel && !input.getAttribute('aria-label')) input.setAttribute('aria-label', input.placeholder || text('Ամբիոն', 'Chair'));
    input.addEventListener('input', () => clear(input));
    input.addEventListener('change', () => clear(input));
  }
  email.maxLength=255;password.maxLength=128;
  if(first)first.maxLength=100;if(last)last.maxLength=100;
  email.autocomplete = 'username'; password.autocomplete = register ? 'new-password' : 'current-password';
  if (chair) chair.options[0].value = '';
  const status = document.createElement('p'); status.setAttribute('role', 'alert'); status.className = 'pr-form-status'; button.before(status);
  function clear(input) {
    document.getElementById(input.id + '-validation')?.remove(); input.removeAttribute('aria-invalid'); input.removeAttribute('aria-describedby');
  }
  function error(input, message) {
    clear(input); const note = document.createElement('p'); note.id = input.id + '-validation';
    note.className = 'error-message show'; note.textContent = message;
    const label = input.closest('.auth-name-field')?.querySelector('label');
    if (label) label.after(note); else input.after(note);
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
    if (register && password.value && password.value.length < 12) {
      error(password, text('Գաղտնաբառը պետք է ունենա առնվազն 12 նիշ։', 'Use at least 12 characters.')); valid = false;
    }
    if (!valid) { container.querySelector('[aria-invalid="true"]')?.focus(); return; }
    button.disabled = true;
    try {
      const result = await ProfRatesAPI.save(register ? '/api/auth/register' : '/api/auth/login', 'POST', {
        Email: email.value.trim(), Password: password.value,
        ...(!register ? {RememberMe: Boolean(container.querySelector('.check')?.checked)} : {}),
        ...(register ? {Language: document.documentElement.lang === 'en' ? 'en' : 'hy'} : {})
      });
      // A redirect alone is never proof that a server authenticated the student.
      if (!register) {
        const state = await ProfRatesSession.check();
        if (!state.authenticated) throw new Error(text('Մուտքը սերվերում չի հաստատվել։', 'The server has not verified this sign-in.'));
        location.href = safeNext(new URLSearchParams(location.search).get('next'));
      } else {
        dialog(result.message, location.href, false);
      }
    } catch (e) {
      const messages={
        'Registration is unavailable. Contact the university administrator.':text('Այս հասցեով գրանցումը հասանելի չէ։ Դիմեք համալսարանի ադմինիստրատորին։','Registration is unavailable. Contact the university administrator.'),
        'This email is already registered. Try signing in or requesting recovery.':text('Այս հասցեով հաշիվ արդեն կա։ Մուտք գործեք կամ վերականգնեք գաղտնաբառը։','This email already has an account. Sign in or reset your password.')
      };
      status.textContent = messages[e.message] || e.message;
    }
    finally { button.disabled = false; }
  }
  button.onclick = submit;
  container.addEventListener('keydown', event => { if (event.key === 'Enter') submit(event); });
  const next = new URLSearchParams(location.search).get('next');
  if (next) for (const link of document.querySelectorAll('a[href*="login_"],a[href*="sign_up_"]')) link.search = '?next=' + encodeURIComponent(safeNext(next));
})();
