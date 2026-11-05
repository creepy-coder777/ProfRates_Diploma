window.ProfRatesRatings = {
  current: null,
  async submit(payload) {
    return ProfRatesAPI.save(this.current ? '/api/ratings/' + this.current.RatingID : '/api/ratings',
      this.current ? 'PUT' : 'POST', this.current ? {...payload, expected_updated_at: this.current.UpdatedAt} : payload);
  },
  async context() {
    const params = new URLSearchParams(location.search);
    const ident = Number(params.get('rating_id'));
    if (ident) {
      this.current = await ProfRatesAPI.request('/api/me/ratings/' + ident);
      for (const [key, value] of Object.entries({lecturer_id: this.current.LecturerID, course_id: this.current.CourseID, term_id: this.current.TermID})) params.set(key, value);
      history.replaceState(null, '', '?' + params);
      return {rating: this.current, questions: (await ProfRatesAPI.request('/api/me/ratings/' + ident + '/questions')).items};
    }
    const data = await ProfRatesAPI.request('/api/me/rating-options');
    const lecturer = Number(params.get('lecturer_id'));
    const options = data.items.filter(item => !lecturer || item.LecturerID === lecturer);
    if(!options.length)return {readOnly:true,notice:location.pathname.includes('eng')?'No eligible courses are linked to your account.':'Ձեր հաշվին գնահատման համար հասանելի առարկա կապված չէ։'};
    const select = document.createElement('select');select.className='rating-options';
    select.setAttribute('aria-label', 'Առարկա / Course');
    const placeholder = document.createElement('option'); placeholder.value = ''; placeholder.textContent = 'Ընտրեք առարկան / Select course'; select.append(placeholder);
    for (const item of options) {
      const option = document.createElement('option'); option.value = JSON.stringify(item); option.textContent = `${item.Name} (${item.TermID})`; select.append(option);
      if (Number(params.get('course_id')) === item.CourseID && Number(params.get('term_id')) === item.TermID) option.selected = true;
    }
    const apply = () => {
      if (!select.value) { params.delete('course_id'); params.delete('term_id'); }
      else { const item = JSON.parse(select.value); params.set('course_id', item.CourseID); params.set('term_id', item.TermID); params.set('lecturer_id', item.LecturerID); }
      history.replaceState(null, '', '?' + params);
    };
    select.onchange = apply; document.querySelector('.review-section').before(select);
    if (options.length === 1) select.selectedIndex = 1;
    apply(); return {};
  }
};
