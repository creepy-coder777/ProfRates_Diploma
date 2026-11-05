(async () => {
 const api=ProfRatesAPI,english=location.pathname.includes('eng'),id=Number(new URLSearchParams(location.search).get('lecturer_id'));
 const main=document.querySelector('main'),status=document.createElement('p');status.setAttribute('role','status');main.prepend(status);
 const set=(selector,value)=>{const e=document.querySelector(selector);if(e)e.textContent=value;};
 const fallback='/frontend/avatar-neutral.svg';
 const viewer=ProfRatesSession.check();
 async function distribution(){
  const stats=await api.request('/api/lecturers/'+id+'/statistics'),counts=new Map(stats.distribution.map(x=>[Number(x.score),Number(x.count)]));
  const total=stats.distribution.reduce((sum,x)=>sum+Number(x.count),0);
  for(const row of document.querySelectorAll('.rating-row.dist')){
   const score=Number(row.querySelector('.rating-label span').textContent.trim()),count=counts.get(score)||0,percent=total?count*100/total:0;
   row.querySelector('.rating-bar').style.width=percent+'%';row.querySelector('.rating-percentage').textContent=Math.round(percent)+'%';row.title=count+' / '+total;
  }
  const note=document.createElement('p');note.className='distribution-note';note.textContent=english?'Distribution of questionnaire answers (1–5).':'Հարցաշարի պատասխանների բաշխում՝ 1–5 միավորով։';document.querySelector('.rating-distribution').append(note);
 }
 try {
  if(!id)throw new Error(english?'Select a lecturer from the home page.':'Ընտրեք դասախոսին գլխավոր էջից։');
  const l=await api.request('/api/lecturers/'+id),name=[l.FirstName,l.MiddleName,l.LastName].filter(Boolean).join(' ');
  document.title='ProfRates — '+name;set('.professor-name',name);set('.professor-department',l.Chairs.join(', '));set('.professor-bio',l.Description||'');
  set('.rating-text',l.AverageScore==null?'—':l.AverageScore+'/5');set('.reviews-count','('+String(l.TotalRatings??0)+(english?' ratings)':' գնահատում)'));
  const display=document.querySelector('.rating-display');display.querySelector('.star-large')?.remove();
  const stars=document.createElement('span');stars.className='rating-stars';stars.setAttribute('aria-label',l.AverageScore==null?(english?'No ratings':'Գնահատումներ չկան'):l.AverageScore+' / 5');
  for(let index=0;index<5;index++){const star=document.createElement('span');star.className='rating-star-fill';star.textContent='★';star.setAttribute('aria-hidden','true');star.style.setProperty('--fill',Math.max(0,Math.min(1,Number(l.AverageScore||0)-index))*100+'%');stars.append(star);}display.prepend(stars);
  const image=document.querySelector('.professor-image');image.src=l.PhotoUrl||fallback;image.alt=name;image.classList.toggle('is-placeholder',!l.PhotoUrl);image.onerror=()=>{image.onerror=null;image.src=fallback;image.classList.add('is-placeholder');};
  const rate=document.querySelector('.rate-btn');if(rate)rate.onclick=async()=>{const next=(english?'rate_eng.html':'rate_arm.html')+'?lecturer_id='+id;if(await ProfRatesSession.requireStudent(next))location.href=next;};
  for(const link of document.querySelectorAll('a[href*="prof_arm"],a[href*="prof_eng"]'))link.search='?lecturer_id='+id;
  const opinions=document.querySelector('.students-opinion'),controls=document.createElement('div'),more=document.createElement('button'),feedback=document.createElement('p');
  controls.className='view-top-container';more.className='view-top-btn';more.type='button';more.textContent=english?'Load more':'Բեռնել ավելին';
  feedback.setAttribute('role','status');feedback.setAttribute('aria-live','polite');controls.append(more);opinions.append(feedback,controls);
  let current=0,busy=false;const seen=new Set();
  function cardFor(r){
   const card=document.createElement('article');card.className='review-card';card.dataset.ratingId=r.RatingID;
   const header=document.createElement('div');header.className='review-header';const avatar=document.createElement('div');avatar.className='reviewer-avatar';
   const anonymous=document.createElement('img');anonymous.src=fallback;anonymous.alt=english?'Anonymous':'Անանուն';avatar.append(anonymous);
   const date=document.createElement('span');date.className='review-date';const parsed=new Date(r.CreatedAt);date.textContent=Number.isNaN(parsed.getTime())?'':(english?parsed.toLocaleDateString('en-GB',{year:'numeric',month:'long',day:'numeric'}):parsed.getDate()+' '+['հունվարի','փետրվարի','մարտի','ապրիլի','մայիսի','հունիսի','հուլիսի','օգոստոսի','սեպտեմբերի','հոկտեմբերի','նոյեմբերի','դեկտեմբերի'][parsed.getMonth()]+', '+parsed.getFullYear());header.append(avatar,date);
   const text=document.createElement('p');text.className='review-text';text.textContent=r.Comment;
   const actions=document.createElement('div');actions.className='review-actions';const like=document.createElement('button'),dislike=document.createElement('button');
   like.className='action-btn like-btn';dislike.className='action-btn dislike-btn';like.type=dislike.type='button';like.setAttribute('aria-label',english?'Like':'Հավանել');dislike.setAttribute('aria-label',english?'Dislike':'Չհավանել');
   let selected=null;const paint=d=>{selected=d.reaction??null;like.textContent='👍 '+Number(d.Likes||0);dislike.textContent='👎 '+Number(d.Dislikes||0);like.setAttribute('aria-pressed',String(selected===1));dislike.setAttribute('aria-pressed',String(selected===-1));};paint(r);
   const react=async value=>{
    if(like.disabled||dislike.disabled)return;
    like.disabled=dislike.disabled=true;
    const signInMessage=english?'Sign in with a student account to react.':'Արձագանքելու համար մուտք գործեք ուսանողի հաշվով։';
    try{
     const session=await ProfRatesSession.check();
     if(!session.authenticated||session.role!=='student'){
      feedback.textContent=session.error?.message||signInMessage;
      ProfRatesSession.dialog(feedback.textContent,location.href,!session.error);return;
     }
     const cancel=selected===value,result=await api.request('/api/ratings/'+r.RatingID+(cancel?'/reaction':value===1?'/like':'/dislike'),{method:cancel?'DELETE':'PUT'});
     paint(result);feedback.textContent='';
    }catch(e){
     const needsAccount=e.status===401||e.status===403;
     feedback.textContent=needsAccount?signInMessage:e.message;
     ProfRatesSession.dialog(feedback.textContent,location.href,needsAccount);
    }finally{like.disabled=dislike.disabled=false;}
   };
   like.onclick=()=>react(1);dislike.onclick=()=>react(-1);actions.append(like,dislike);card.append(header,text,actions);
   // A guest URL can still be opened by a signed-in student.
   // Restore the persisted selection before enabling reaction controls.
   like.disabled=dislike.disabled=true;
   viewer.then(async session=>{
    if(session.authenticated && session.role==='student')paint(await api.request('/api/ratings/'+r.RatingID+'/reaction'));
   }).catch(e=>{feedback.textContent=e.message;}).finally(()=>{like.disabled=dislike.disabled=false;});
   return card;
  }
  async function loadMore(){
   if(busy)return;busy=true;more.disabled=true;
   try{const data=await api.request('/api/lecturers/'+id+'/comments?page='+(current+1)+'&page_size=20');for(const r of data.items){if(seen.has(r.RatingID))continue;opinions.insertBefore(cardFor(r),feedback);seen.add(r.RatingID);}current=data.page;more.hidden=current*data.page_size>=data.total||!data.items.length;feedback.textContent=data.total?'':(english?'No comments yet.':'Մեկնաբանություններ չկան։');}catch(e){feedback.textContent=e.message;}finally{busy=false;more.disabled=false;}
  }
  more.onclick=loadMore;await Promise.all([loadMore(),distribution().catch(e=>{status.textContent=e.message;})]);
 }catch(e){status.textContent=e.message;const b=document.querySelector('.rate-btn');if(b)b.disabled=true;}
})();
