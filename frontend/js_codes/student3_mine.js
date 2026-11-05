(async () => {
 const {text}=ProfRatesSession, grid=document.getElementById('ratingsGrid'), subtitle=document.querySelector('.subtitle');
 const status=document.createElement('p'); status.setAttribute('role','status'); grid.before(status);
 grid.replaceChildren(); subtitle.textContent=''; let page=0,total=0,shown=0,busy=false;
 const more=document.createElement('button'); more.type='button'; more.className='pr-button pr-more'; more.textContent=text('Ավելին','More'); more.hidden=true; grid.after(more);
 const count=()=>{subtitle.textContent=text('Ուղարկված գնահատումներ՝ ','Ratings submitted: ')+total;};
 const state=await ProfRatesSession.ready;
 if(!state.authenticated) { status.textContent=text('Այս էջը հասանելի է միայն մուտք գործած ուսանողներին։','This page is available to signed-in students only.'); await ProfRatesSession.requireStudent(); return; }
 const en=document.documentElement.lang.startsWith('en'),node=(tag,cls,value)=>{const n=document.createElement(tag);n.className=cls;if(value!==undefined)n.textContent=value;return n;};
 const statuses={Pending:text('Սպասում է հաստատման','Pending moderation'),Approved:text('Հաստատված','Approved'),Rejected:text('Մերժված','Rejected')};
 async function load() {
  if(busy)return;busy=true;more.disabled=true;
  try {
   const result=await ProfRatesAPI.request('/api/me/ratings?page='+(page+1));
   for(const rating of result.items) {
    const card=node('article','rate-card'), info=node('div','rate-info'), avatar=node('div','avatar'),photo=node('a','');
    photo.href=(en?'prof_eng.html':'prof_arm.html')+'?lecturer_id='+rating.LecturerID;
    const image=node('img','');image.src='avatar-neutral.svg';image.alt=text('Դասախոս','Lecturer');photo.append(image);avatar.append(photo);
    const name=node('h2','prof-name',text('Դասախոս №','Lecturer #')+rating.LecturerID);
    const review=node('p','rate-text',rating.Comment||text('Առանց մեկնաբանության','No comment'));
    const scores=rating.answers||[],average=scores.length?scores.reduce((sum,a)=>sum+Number(a.Score),0)/scores.length:null;
    const score=node('p','rating-num',average===null?'—':average.toFixed(2)+' / 5');
    const date=node('p','rate-date',new Date(rating.CreatedAt).toLocaleDateString(en?'en-GB':'hy-AM'));
    const label=node('p','rating-status',statuses[rating.Status]||rating.Status);
    info.append(name,score,review,label,date);
    const actions=node('div','card-actions'),edit=node('a','icon-btn edit-btn','✎'),remove=node('button','icon-btn delete-btn','×');
    edit.setAttribute('aria-label',text('Խմբագրել','Edit'));edit.href=(en?'rate_eng.html':'rate_arm.html')+'?rating_id='+rating.RatingID;
    remove.type='button';remove.setAttribute('aria-label',text('Ջնջել','Delete'));
    remove.onclick=async()=>{
     if(!confirm(text('Ջնջե՞լ գնահատումը։','Delete this rating?')))return;remove.disabled=true;
     try {await ProfRatesAPI.request('/api/ratings/'+rating.RatingID+'?expected_updated_at='+encodeURIComponent(rating.UpdatedAt),{method:'DELETE'});card.remove();total--;shown--;count();status.textContent=total?'':text('Դեռ գնահատումներ չկան։','No ratings yet.');more.hidden=shown>=total;}
     catch(e){status.textContent=e.message;}finally{remove.disabled=false;}
    };
    actions.append(edit,remove);card.append(avatar,info,actions);grid.append(card);shown++;
    ProfRatesAPI.request('/api/lecturers/'+rating.LecturerID).then(lecturer=>{
     name.textContent=[lecturer.FirstName,lecturer.LastName].filter(Boolean).join(' ');image.alt=name.textContent;
     if(lecturer.PhotoUrl)image.src=lecturer.PhotoUrl;
     image.onerror=()=>{image.onerror=null;image.src='avatar-neutral.svg';};
    }).catch(()=>{});
   }
   page=result.page;total=result.total;count();status.textContent=total?'':text('Դեռ գնահատումներ չկան։','No ratings yet.');more.hidden=shown>=total;
  } catch(e) {status.textContent=e.message;more.hidden=false;more.textContent=text('Փորձել կրկին','Try again');}
  finally{busy=false;more.disabled=false;}
 }
 more.onclick=load;await load();
 window.addEventListener('pageshow',event=>{if(event.persisted)location.reload();});
})();
