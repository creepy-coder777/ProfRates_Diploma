(async()=>{const trText=ProfRatesI18n.t;const {el,show,run,button,pager}=S2;const api=ProfRatesAPI;let current=1;const tbody=document.querySelector('.reviews-table tbody');tbody.replaceChildren();
 const filter=document.querySelector('.filter-dropdown');filter.replaceChildren();for(const [v,t]of[['','Բոլորը'],['Pending','Սպասման մեջ'],['Approved','Հաստատված'],['Rejected','Մերժված']])filter.append(new Option(trText(t),v));
 const search=document.querySelector('.search-bar input');const pages=pager(load);document.querySelector('.reviews-table').after(pages.node);
 const query=()=>new URLSearchParams({page:current,page_size:20,q:search.value,...(filter.value?{status:filter.value}:{})});
 document.querySelector('.header-actions').append(button('Արտահանել էջը',()=>api.download('/api/admin/comments/export?'+query(),'comments.csv'),'export-btn'));
 async function load(page=1){current=page;tbody.replaceChildren();const data=await api.request('/api/admin/comments?'+query());
  for(const c of data.items){const tr=el('tr');for(const val of [c.LecturerName,c.StudentName,c.OverallScore??'—',c.Comment,c.CreatedAt,c.Status])tr.append(el('td','',val,true));const a=el('td');
   for(const [status,label] of [['Approved','Հաստատել'],['Rejected','Մերժել']])if(c.Status!==status)a.append(button(label,async()=>{
    if(!confirm(trText('Փոփոխությունը կազդի ամբողջ գնահատման հրապարակման և վարկանիշում ընդգրկվելու վրա։ Շարունակե՞լ։')))return;
    await api.save('/api/admin/comments/'+c.RatingID+'/moderation','PUT',{status,expected_status:c.Status});await load(current);
   }));tr.append(a);tbody.append(tr);
  }pages.update(data);show(data.total?'':'Մեկնաբանություններ չկան։');
 }
 filter.onchange=()=>run(()=>load(1));search.oninput=()=>{clearTimeout(search.timer);search.timer=setTimeout(()=>run(()=>load(1)),300);};await run(load);
})();
