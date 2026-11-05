(async () => {
 const {text}=ProfRatesSession,api=ProfRatesAPI,main=document.querySelector('main'),button=document.querySelector('.submit-btn'),review=document.getElementById('reviewText');
 const status=document.createElement('p');status.setAttribute('role','alert');status.className='rating-access-note';button.before(status);
 const answers=new Map(),rows=new Map();let questions=[],readOnly=false,loaded=false,saving=false;
 const labels=[text('Բոլորովին համաձայն չեմ','Strongly disagree'),text('Համաձայն չեմ','Disagree'),text('Մասամբ համաձայն եմ','Partly agree'),text('Համաձայն եմ','Agree'),text('Լիովին համաձայն եմ','Strongly agree')];
 const note=message=>{status.textContent=message;};
 review.oninput=()=>{document.getElementById('charCount').textContent=review.value.length;};
 window.submitRating=async()=>{
  if(saving)return;
  if(!loaded){const message=text('Հարցաշարը դեռ չի բեռնվել։ Փորձեք թարմացնել էջը։','The questionnaire has not loaded. Try refreshing the page.');note(message);ProfRatesSession.dialog(message,location.href,false);return;}
  if(readOnly){const message=text('Ձեր հաշվին այս դասախոսի համար հասանելի առարկա չկա։','No eligible course is linked to your account for this lecturer.');note(message);ProfRatesSession.dialog(message,location.href,false);return;}
  const missing=questions.filter(q=>!answers.has(q.QuestionID));for(const [id,row]of rows)row.classList.toggle('pr-unanswered',!answers.has(id));
  if(missing.length||!questions.length){
   const message=text('Խնդրում ենք պատասխանել բոլոր հարցերին։ Չլրացված հարցեր՝ ','Please answer all questions. Unanswered: ')+missing.length;note(message);ProfRatesSession.dialog(message,location.href,false);
   rows.get(missing[0]?.QuestionID)?.scrollIntoView({block:'center',behavior:'smooth'});return;
  }
  if(!await ProfRatesSession.requireStudent())return;
  const context=Object.fromEntries(new URLSearchParams(location.search));
  const payload={LecturerID:Number(context.lecturer_id),CourseID:Number(context.course_id),TermID:Number(context.term_id),answers:questions.map(q=>({QuestionID:q.QuestionID,Score:answers.get(q.QuestionID)})),Comment:review.value.trim()||null};
  if(!payload.LecturerID||!payload.CourseID||!payload.TermID){const message=text('Ընտրեք առարկան և ուսումնական շրջանը։','Select a course and academic term.');note(message);ProfRatesSession.dialog(message,location.href,false);document.querySelector('.rating-options')?.focus();return;}
  saving=true;button.disabled=true;
  try {
   const result=await ProfRatesRatings.submit(payload);
   const message=result.Status==='Pending'?text('Գնահատումը հաջողությամբ պահպանվել է։ Մեկնաբանությունը սպասում է հաստատման։','Your rating was saved. The comment is awaiting moderation.'):text('Գնահատումը հաջողությամբ պահպանվել է։','Your rating was saved successfully.');
   note(message);
   const modal=ProfRatesSession.dialog(message,location.href,false);
   modal.querySelector('button').textContent=text('Իմ գնահատականները','My ratings');
   modal.addEventListener('close',()=>{location.href=text('ratings_arm.html','ratings_eng.html');},{once:true});
   button.textContent=text('Պահպանված է','Saved');
  } catch(e){note(e.message);if(e.status===401)await ProfRatesSession.requireStudent();else ProfRatesSession.dialog(e.message,location.href,false);saving=false;button.disabled=false;}
 };
 button.removeAttribute('onclick');button.type='button';button.onclick=event=>{event.preventDefault();return window.submitRating();};
 button.disabled=true;
 try {
  questions=(await api.request('/api/questions')).items;
  let context={};const state=await ProfRatesSession.ready;
  if(state.authenticated){context=await ProfRatesRatings.context();}
  else{readOnly=true;note(text('Հարցաշարը կարող եք դիտել։ Ուղարկելու համար մուտք գործեք։','You can preview this questionnaire. Sign in to submit.'));await ProfRatesSession.requireStudent();}
  readOnly=readOnly||Boolean(context.readOnly);
  if(context.questions)questions=context.questions;
  if(context.rating){review.value=context.rating.Comment||'';review.oninput();for(const answer of context.rating.answers)answers.set(answer.QuestionID,answer.Score);}
  const anchor=document.querySelector('.review-section'),groups=new Map();
  for(const question of questions){if(!groups.has(question.Category))groups.set(question.Category,[]);groups.get(question.Category).push(question);}
  for(const [category,items]of groups){
   const section=document.createElement('section');section.className='rating-section';const title=document.createElement('h2');title.className='section-title';title.textContent=category;section.append(title);
   for(const question of items){
    const row=document.createElement('div');row.className='question-item';rows.set(question.QuestionID,row);
    const label=document.createElement('div');label.className='question-text';label.textContent=question.Text;label.id='question-'+question.QuestionID;
    const wrap=document.createElement('div');wrap.className='scale-wrapper';const scale=document.createElement('div');scale.className='scale';scale.setAttribute('role','radiogroup');scale.setAttribute('aria-labelledby',label.id);
    const selected=document.createElement('div');selected.className='selected-text';
    for(let score=1;score<=5;score++){
     const segment=document.createElement('div');segment.className='segment';segment.tabIndex=0;segment.setAttribute('role','radio');segment.setAttribute('aria-label',score+': '+labels[score-1]);segment.setAttribute('aria-checked','false');
     segment.onclick=()=>{answers.set(question.QuestionID,score);row.classList.remove('pr-unanswered');[...scale.children].forEach((s,index)=>{s.className='segment'+(index<score?' pos-'+(index+1):'');s.setAttribute('aria-checked',String(index+1===score));});selected.textContent=labels[score-1];};
     segment.onkeydown=event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();segment.click();}};scale.append(segment);
    }
    if(answers.has(question.QuestionID))scale.children[answers.get(question.QuestionID)-1]?.click();
    wrap.append(scale,selected);row.append(label,wrap);section.append(row);
   }anchor.before(section);
  }
  loaded=true;button.disabled=false;
  if(context.notice)note(context.notice);
  if(!questions.length)note(text('Ակտիվ հարցեր չկան։','There are no active questions.'));
  const lecturer=new URLSearchParams(location.search).get('lecturer_id');
  if(lecturer){const result=await api.request('/api/lecturers/'+Number(lecturer));document.querySelector('.page-title').textContent=[result.FirstName,result.LastName].filter(Boolean).join(' ');document.querySelector('.subtitle').textContent=result.Description||'';}
 }catch(e){note(e.message);button.disabled=false;}
})();
