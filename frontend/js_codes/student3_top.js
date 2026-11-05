(async () => {
  const grid=document.getElementById('profGrid'),filter=document.getElementById('departmentFilter'),sort=document.getElementById('sortFilter'),search=document.getElementById('searchInput');
  const english=location.pathname.includes('eng'),guest=location.pathname.includes('guest');
  const status=document.createElement('p');status.setAttribute('role','status');grid.before(status);grid.replaceChildren();
  let page=1; const pageSize=3;
  const pages=document.createElement('nav');pages.className='pagination';pages.setAttribute('aria-label',english?'Pages':'Էջեր');grid.after(pages);
  const element=(tag,cls,text)=>{const n=document.createElement(tag);n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  try {
    const data=(await ProfRatesAPI.request('/api/rankings')).items;
    filter.replaceChildren(new Option(english?'All departments':'Բոլոր ամբիոնները',''));
    for(const name of [...new Set(data.flatMap(x=>x.Chairs))].sort())filter.append(new Option(name,name));
    function render(){
      let items=data.filter(x=>(!filter.value||x.Chairs.includes(filter.value))&&[x.FirstName,x.MiddleName,x.LastName].join(' ').toLowerCase().includes(search.value.trim().toLowerCase()));
      if(sort.value==='lowest')items.sort((a,b)=>a.BayesianScore-b.BayesianScore);
      else if(sort.value==='a-z'||sort.value==='z-a')items.sort((a,b)=>(sort.value==='z-a'?-1:1)*a.FirstName.localeCompare(b.FirstName));
      else items.sort((a,b)=>b.BayesianScore-a.BayesianScore||b.TotalRatings-a.TotalRatings||a.LecturerID-b.LecturerID);
      grid.replaceChildren();status.textContent=items.length?'':(english?'No lecturers found':'Դասախոսներ չեն գտնվել');
      page=Math.max(1,Math.min(page,Math.ceil(items.length/pageSize)||1));
      pages.replaceChildren();
      if(items.length>pageSize){
        for(const [label,target,disabled] of [[english?'Previous':'Նախորդ',page-1,page<=1],[english?'Next':'Հաջորդ',page+1,page*pageSize>=items.length]]){
          const button=element('button','pr-page-btn',label);button.type='button';button.disabled=disabled;button.onclick=()=>{page=target;render();grid.scrollIntoView({block:'start'});};pages.append(button);
        }
      }
      for(const x of items.slice((page-1)*pageSize,page*pageSize)){
        const name=[x.FirstName,x.MiddleName,x.LastName].filter(Boolean).join(' '),card=element('article','prof-card'),content=element('div','card-content'),avatar=element('div','avatar'),img=element('img','');
        const photo=document.createElement('a');photo.href=(english?(guest?'prof_eng_guest.html':'prof_eng.html'):(guest?'prof_arm_guest.html':'prof_arm.html'))+'?lecturer_id='+x.LecturerID;photo.setAttribute('aria-label',name);img.src=x.PhotoUrl||'/frontend/avatar-neutral.svg';img.alt=name;img.onerror=()=>{img.onerror=null;img.src='/frontend/avatar-neutral.svg';};photo.append(img);avatar.append(photo);
        const score=x.AverageScore==null?(english?'Not rated yet':'Դեռ գնահատված չէ'):Number(x.AverageScore).toFixed(2)+' / 5';
        content.append(avatar,element('div','prof-name',name),element('div','rating-num',(english?'Average: ':'Միջին՝ ')+score),element('div','rating-count',(english?'Ratings: ':'Գնահատումներ՝ ')+x.TotalRatings),element('div','department',x.Chairs.join(', ')),element('div','bio',x.Description||''));
        const button=element('button','rate-btn',english?'Rate now':'Գնահատել');button.type='button';
        button.textContent=english?'Rate now':'Գնահատել';button.onclick=async()=>{const next=(english?'rate_eng.html':'rate_arm.html')+'?lecturer_id='+x.LecturerID;if(await ProfRatesSession.requireStudent(next))location.href=next;};
        card.append(content,button);grid.append(card);
      }
    }
    const note=element('p','pr-ranking-info',english?'Ranking follows the database ranking method. Average score and number of ratings are shown separately.':'Դասավորությունը՝ բազայի վարկանիշի հաշվարկով։ Միջին գնահատականն ու գնահատումների քանակը ներկայացված են առանձին։');grid.before(note);
    filter.onchange=sort.onchange=search.oninput=()=>{page=1;render();};render();
  }catch(e){status.textContent=e.message;}
})();
