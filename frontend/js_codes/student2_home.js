(async () => {
 const api=ProfRatesAPI, en=document.documentElement.lang.startsWith('en'), text=(hy,eng)=>en?eng:hy;
 const grid=document.getElementById('professorsGrid'), search=document.getElementById('searchInput'), chair=document.getElementById('chairFilter'), sort=document.getElementById('sortFilter');
 const message=document.createElement('p'); message.setAttribute('role','status'); grid.before(message);
 const pages=document.createElement('nav'); pages.className='pagination'; pages.setAttribute('aria-label',text('Էջեր','Pages')); grid.after(pages);
 const node=(tag,cls,value)=>{const n=document.createElement(tag); n.className=cls; if(value!==undefined)n.textContent=value; return n;};
 let sequence=0;
 async function load(page=1) {
  const ticket=++sequence; message.textContent=text('Բեռնվում է…','Loading…'); pages.replaceChildren();
  try {
   const params=new URLSearchParams({q:search.value,page,page_size:4,sort:sort.value||'id',...(chair.value?{chair_id:chair.value}:{})});
   const data=await api.request('/api/lecturers?'+params); if(ticket!==sequence)return; grid.replaceChildren();
   for(const lecturer of data.items) {
    const name=[lecturer.FirstName,lecturer.LastName].filter(Boolean).join(' '), card=node('article','professor-card');
    const photo=node('a','professor-photo-link'); photo.href=(en?'prof_eng_guest.html':'prof_arm_guest.html')+'?lecturer_id='+lecturer.LecturerID; photo.setAttribute('aria-label',text('Դիտել՝ ','View ')+name);
    const image=node('img','professor-image'); image.src=lecturer.PhotoUrl||'avatar-neutral.svg'; image.alt=name; image.classList.toggle('is-placeholder',!lecturer.PhotoUrl);
    image.onerror=()=>{image.onerror=null;image.src='avatar-neutral.svg';image.classList.add('is-placeholder');}; photo.append(image);
    const info=node('div','professor-info'), heading=node('h2','professor-name',name), rating=node('div','rating');
    for(let i=0;i<5;i++) { const star=node('span','rating-star-fill','★'); star.setAttribute('aria-hidden','true'); star.style.setProperty('--fill',Math.max(0,Math.min(1,Number(lecturer.AverageScore||0)-i))*100+'%'); rating.append(star); }
    const score=lecturer.AverageScore==null?text('Դեռ գնահատված չէ','Not rated yet'):Number(lecturer.AverageScore).toFixed(2)+' / 5';
    rating.setAttribute('aria-label',score); rating.append(node('span','rating-number',score));
    info.append(heading,rating,node('div','professor-department',(lecturer.Chairs||[]).join(', ')),node('p','professor-description',lecturer.Description||'')); card.append(photo,info); grid.append(card);
   }
   message.textContent=data.total?text('Դասախոսներ՝ ','Lecturers: ')+data.total:text('Դասախոսներ չեն գտնվել։','No lecturers found.');
   if(data.total>data.page_size) {
    for(const [label,target,disabled] of [[text('Նախորդ','Previous'),page-1,page<=1],[text('Հաջորդ','Next'),page+1,page*data.page_size>=data.total]]) {
     const button=node('button','pr-page-btn',label); button.type='button'; button.disabled=disabled; button.onclick=()=>load(target); pages.append(button);
    }
   }
  } catch(error) { if(ticket!==sequence)return;grid.replaceChildren();message.textContent=error.message; }
 }
 chair.replaceChildren(new Option(text('Բոլոր ամբիոնները','All departments'),''));
 try { for(let page=1;;page++) { const result=await api.request('/api/academic/chairs?page_size=100&page='+page); for(const item of result.items)chair.append(new Option(item.Name,item.ChairID)); if(page*result.page_size>=result.total)break; } } catch(error) {message.textContent=error.message;}
 chair.onchange=sort.onchange=()=>load(); search.oninput=()=>{clearTimeout(search.timer);search.timer=setTimeout(()=>load(),300);}; await load();
})();
