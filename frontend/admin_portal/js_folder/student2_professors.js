(async()=>{const trText=ProfRatesI18n.t;const {el,show,run,button,form,pager,all}=S2;const api=ProfRatesAPI;
 const fields={FirstName:'text',LastName:'text',MiddleName:'text',Title:'text',PhotoUrl:'text',Description:'textArea',IsActive:'checkbox'};
 const tbody=document.querySelector('.professors-table tbody');tbody.replaceChildren();let current=1;
 const search=document.querySelector('.search-bar input');const active=el('select','filter-dropdown');
 for(const [v,t] of [['','Բոլոր կարգավիճակները'],['true','Ակտիվ'],['false','Պասիվ']])active.append(new Option(trText(t),v));
 const chair=el('select','filter-dropdown');chair.append(new Option(trText('Բոլոր ամբիոնները'),''));
 document.querySelector('.section-header').append(active,chair);
 const table=document.querySelector('.professors-table');const pages=pager(load);(table.closest('.table-wrap')||table).after(pages.node);
 const query=()=>new URLSearchParams({page:current,page_size:20,q:search.value,...(active.value?{active:active.value}:{}),...(chair.value?{chair_id:chair.value}:{})});
 async function edit(item={}){await form(item.LecturerID?'Խմբագրել դասախոսին':'Ավելացնել դասախոս',fields,item,async body=>{
  await api.save('/api/admin/lecturers'+(item.LecturerID?'/'+item.LecturerID:''),item.LecturerID?'PUT':'POST',body);await load(current);});}
 async function load(page=1){current=page;tbody.replaceChildren();const data=await api.request('/api/admin/lecturers?'+query());
  for(const item of data.items){const tr=el('tr');for(const text of [[item.FirstName,item.MiddleName,item.LastName].filter(Boolean).join(' '),item.Chairs.join(', ')||'—',item.AverageScore??'—',item.TotalRatings??0])tr.append(el('td','',text,true));
   const status=el('td');status.append(el('span','status-badge '+(item.IsActive?'active':''),item.IsActive?'Ակտիվ':'Պասիվ'));tr.append(status);
   const actions=el('td','actions-cell');actions.append(button('Խմբագրել',()=>edit(item)),button('Առարկաներ',()=>{location.href=ProfRatesI18n.page('academic_arm.html','academic.html')+'?resource=courses&lecturer_id='+item.LecturerID;}));
   if(item.IsActive)actions.append(button('Ապաակտիվացնել',async()=>{if(confirm(trText('Ապաակտիվացնե՞լ դասախոսին։'))){await api.request('/api/admin/lecturers/'+item.LecturerID,{method:'DELETE'});await load(current);}}));
   tr.append(actions);tbody.append(tr);
  }pages.update(data);show(data.total?'':'Դասախոսներ չկան։');
 }
 document.querySelector('.add-professor-btn').onclick=()=>run(()=>edit());
 document.querySelector('.export-btn').onclick=()=>run(()=>api.download('/api/admin/lecturers/export?'+query(),'lecturers-page-'+current+'.csv'));
 search.addEventListener('input',()=>{clearTimeout(search.timer);search.timer=setTimeout(()=>run(()=>load(1)),300);});
 active.onchange=chair.onchange=()=>run(()=>load(1));
 await run(async()=>{for(const c of await all('/api/admin/academic/chairs'))chair.append(new Option(c.Name,c.ChairID));await load();});
})();
