(async()=>{const trText=ProfRatesI18n.t;const {el,show,run,button,form}=S2;const api=ProfRatesAPI;const host=document.getElementById('s2Questions');let items=[];
 const fields={Text:'textArea',Category:'text',SortOrder:'number',IsActive:'checkbox'};
 async function edit(q={SortOrder:items.length+1,IsActive:true}){await form('Գնահատման հարց',fields,q,async body=>{
  const result=await api.save('/api/admin/questions'+(q.QuestionID?'/'+q.QuestionID:''),q.QuestionID?'PUT':'POST',body);await load();
  if(result.replaced_question_id)show('Հին հարցի պատասխանները պահպանվել են։ Ստեղծվել է հարցի նոր տարբերակ։');});}
 async function move(q,delta){const ids=items.filter(x=>x.IsActive).map(x=>x.QuestionID);const i=ids.indexOf(q.QuestionID),j=i+delta;
  if(i<0||j<0||j>=ids.length)return;[ids[i],ids[j]]=[ids[j],ids[i]];await api.save('/api/admin/questions/order','PUT',{question_ids:ids});await load();}
 async function load(){host.replaceChildren();items=(await api.request('/api/admin/questions')).items;
  const groups=[];for(const q of items){if(!groups.length||groups[groups.length-1][0]!==q.Category)groups.push([q.Category,[]]);groups[groups.length-1][1].push(q);}
  for(const [category,questions] of groups){const card=el('section','category-card');const header=el('div','category-header');header.append(el('h3','',category,true));card.append(header);
   for(const q of questions){const row=el('div','question-item');row.append(el('div','question-content',`${q.SortOrder}. ${q.Text}`,true),el('span','status-badge',q.IsActive?'Ակտիվ':'Պասիվ'));
    const actions=el('div','question-actions');actions.append(button('Խմբագրել',()=>edit(q)));
    if(q.IsActive)actions.append(button('↑',()=>move(q,-1)),button('↓',()=>move(q,1)),button('Ապաակտիվացնել',async()=>{if(confirm(trText('Ապաակտիվացնե՞լ հարցը։ Նախկին պատասխանները կպահպանվեն։'))){await api.request('/api/admin/questions/'+q.QuestionID,{method:'DELETE'});await load();}}));
    row.append(actions);card.append(row);
   }host.append(card);
  }show(trText('Ակտիվ հարցեր՝ {n}։ Գնահատման էջը բեռնում է նույն ցանկը։',{n:items.filter(x=>x.IsActive).length}));
 }
 document.getElementById('s2AddQuestion').onclick=()=>run(()=>edit());document.querySelector('.export-btn')?.addEventListener('click',()=>run(()=>api.download('/api/admin/questions/export','questions.csv')));
 await run(load);
})();
