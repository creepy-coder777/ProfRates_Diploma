/* Existing admin layout, real server data, no simulated rows or credentials. */
(async () => {
  const en=document.documentElement.lang.startsWith('en'), text=(hy,enText)=>en?enText:hy;
  const path=location.pathname, file=path.split('/').pop(), api=ProfRatesAPI;
  const status=document.createElement('p');status.setAttribute('role','status');status.style.padding='12px';
  (document.querySelector('.main-content,.form-container')||document.body).prepend(status);
  const report=e=>status.textContent=e.message;
  const loginPage=/Admin_login/.test(file);
  function cell(row,value){const td=document.createElement('td');td.textContent=value??'—';row.append(td);return td;}
  function button(label,action){const b=document.createElement('button');b.type='button';b.textContent=label;b.className='action-btn';b.onclick=async()=>{b.disabled=true;try{await action();}catch(e){report(e);}finally{b.disabled=false;}};return b;}
  let dialogNumber=0;
  function accountDialog(title,wide=false){
    const modal=document.createElement('dialog');modal.className='account-dialog'+(wide?' account-dialog-wide':'');
    const header=document.createElement('div');header.className='account-dialog-header';
    const heading=document.createElement('h2');heading.id='account-dialog-title-'+(++dialogNumber);heading.textContent=title;
    const close=document.createElement('button');close.type='button';close.className='account-dialog-close';close.textContent='×';close.setAttribute('aria-label',text('Փակել','Close'));close.onclick=()=>modal.close();
    header.append(heading,close);const content=document.createElement('div');content.className='account-dialog-content';modal.append(header,content);modal.setAttribute('aria-labelledby',heading.id);
    modal.addEventListener('close',()=>modal.remove(),{once:true});
    modal.addEventListener('click',event=>{if(event.target===modal){const r=modal.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)modal.close();}});
    return {modal,content};
  }
  if(loginPage){
    const form=document.querySelector('form');
    form.querySelector('#email').required=true;form.querySelector('#password').required=true;
    form.onsubmit=async event=>{
      event.preventDefault();const submit=form.querySelector('[type=submit]');submit.disabled=true;status.textContent='';
      try{await api.save('/api/auth/admin/login','POST',{Email:document.getElementById('email').value.trim(),Password:document.getElementById('password').value});location.href=en?'dashboard.html':'dashboard_arm.html';}
      catch(e){report(e);}finally{submit.disabled=false;}
    };
    const recover=document.createElement('a');recover.href='account_recovery_'+(en?'eng':'arm')+'.html';recover.textContent=text('Վերականգնել գաղտնաբառը','Reset administrator password');form.append(recover);return;
  }
  try{
    const session=await api.request('/api/auth/session');
    if(session.role!=='admin')throw new Error(text('Պահանջվում է ադմինի հաշիվ։','Administrator account required.'));
  }catch(e){location.replace(en?'Admin_login_eng.html':'Admin_login_arm.html');return;}
  const logout=button(text('Ելք','Sign out'),async()=>{await api.save('/api/auth/logout','POST',{});location.href=en?'Admin_login_eng.html':'Admin_login_arm.html';});
  document.querySelector('.sidebar-footer')?.before(logout);
  document.querySelectorAll('.user-details h3').forEach(x=>x.textContent='…');
  document.querySelectorAll('.user-details p').forEach(x=>x.textContent='');
  if(file.startsWith('dashboard')){
    document.querySelectorAll('.stat-value').forEach(x=>x.textContent='—');
    document.querySelectorAll('.stat-change,.activity-item,.review-item').forEach(x=>x.remove());
  }
  try{
    const d=await api.request('/api/admin/dashboard');
    document.querySelectorAll('.user-details h3').forEach(x=>x.textContent=d.admin.DisplayName||[d.admin.FirstName,d.admin.LastName].filter(Boolean).join(' '));
    document.querySelectorAll('.user-details p').forEach(x=>x.textContent=d.admin.Email);
    if(file.startsWith('dashboard')){
      const values=[d.users,d.lecturers,d.ratings,d.average_score?.toFixed(2)??'—'];
      const labels=document.querySelectorAll('.stat-label');if(labels[3])labels[3].textContent=text('Բոլոր գնահատումների միջին','Average across all ratings');
      document.querySelectorAll('.stat-value').forEach((x,i)=>x.textContent=values[i]);
      document.querySelectorAll('.stat-change').forEach(x=>x.remove());
      document.querySelector('.search-bar')?.remove();
      const sections=document.querySelectorAll('.content-grid .section-card');
      sections[0]?.querySelectorAll('.activity-item').forEach(x=>x.remove());
      for(const item of d.recent_activity){
        const x=document.createElement('div');x.className='activity-item';x.textContent=[item.ActionType,item.Target,item.CreatedAt,item.Status].join(' · ');sections[0]?.append(x);
      }
      sections[1]?.querySelectorAll('.review-item').forEach(x=>x.remove());
      for(const item of d.pending_reviews){
        const x=document.createElement('div');x.className='review-item';
        const note=document.createElement('p');note.textContent=[item.DisplayLecturerName||item.LecturerName,item.Comment,item.OverallScore].join(' · ');x.append(note);
        for(const [value,label] of [['Approved',text('Հաստատել','Approve')],['Rejected',text('Մերժել','Reject')]])
          x.append(button(label,async()=>{await api.save('/api/admin/comments/'+item.RatingID+'/moderation','PUT',{status:value,expected_status:item.Status});location.reload();}));
        sections[1]?.append(x);
      }
      const exportBtn=document.querySelector('.export-btn');
      if(exportBtn)exportBtn.onclick=()=>{const blob=new Blob([JSON.stringify(d,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='dashboard.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
    }
  }catch(e){report(e);}
  let page=1;
  const search=document.querySelector('.search-bar input');
  const tbody=document.querySelector('.users-table tbody,.activity-table tbody,.requests-table tbody');
  const relevant=/^(users|ActivityLogs|ResetPassword)/.test(file);
  if(!relevant)return;
  let endpoint=file.startsWith('users')?'/api/admin/users':file.startsWith('ActivityLogs')?'/api/admin/activity-logs':'/api/admin/password-resets';
  tbody?.replaceChildren();
  // Existing static modal fields cannot safely edit identity or roles.
  document.querySelectorAll('#editModal,#addModal').forEach(x=>x.remove());
  document.querySelectorAll('.filter-dropdown,.filters select,.filters-row select').forEach(x=>x.remove());
  const controls=document.createElement('div');controls.style.padding='16px';let total=0;
  controls.append(button('←',async()=>{if(page>1){page--;await load();}}));
  const pageNote=document.createElement('span');controls.append(pageNote);
  controls.append(button('→',async()=>{if(page*20<total){page++;await load();}}));
  const table=tbody?.closest('table'),tableWrap=table?.closest('.table-wrap');
  (tableWrap||table)?.after(controls);
  async function editUser(item){
    const {modal,content}=accountDialog(text('Ուսանողի հաշիվ','Student account'));const form=document.createElement('form');content.append(form);
    const inputs={};
    for(const [key,label] of [['FirstName',text('Անուն','First name')],['LastName',text('Ազգանուն','Last name')],['GroupID',text('Խմբի ID','Group ID')]]){
      const l=document.createElement('label');l.textContent=label;const input=document.createElement('input');input.value=item[key]??'';input.required=key!=='GroupID';input.maxLength=100;if(key==='GroupID'){input.type='number';input.min=1;}l.append(input);form.append(l);inputs[key]=input;
    }
    const select=document.createElement('select');select.setAttribute('aria-label',text('Կարգավիճակ','Status'));
    for(const [value,label] of [['Active',text('Ակտիվ','Active')],['Suspended',text('Կասեցված','Suspended')],['Banned',text('Արգելափակված','Banned')]])select.append(new Option(label,value));
    select.value=item.Status;form.append(select);
    const save=document.createElement('button');save.textContent=text('Պահպանել','Save');save.type='submit';form.append(save,button(text('Փակել','Close'),()=>modal.close()));
    const note=document.createElement('p');note.setAttribute('role','alert');form.append(note);
    form.onsubmit=async e=>{e.preventDefault();save.disabled=true;try{
      await api.save('/api/admin/users/'+item.UserID,'PUT',{FirstName:inputs.FirstName.value.trim(),LastName:inputs.LastName.value.trim(),GroupID:inputs.GroupID.value?Number(inputs.GroupID.value):null,Status:select.value});
      modal.close();await load();
    }catch(error){note.textContent=error.message;}finally{save.disabled=false;}};
    document.body.append(modal);modal.onclose=()=>modal.remove();modal.showModal();
  }
  async function load(){
    status.textContent='';
    const url=endpoint+'?page='+page+'&page_size=20'+(!file.startsWith('ResetPassword')?'&q='+encodeURIComponent(search?.value||''):'');
    const result=await api.request(url);total=result.total;tbody.replaceChildren();pageNote.textContent=' '+page+' / '+Math.max(1,Math.ceil(total/20))+' ';
    for(const item of result.items){
      const row=document.createElement('tr');
      if(file.startsWith('users')){
        cell(row,item.DisplayName||item.FirstName+' '+item.LastName);cell(row,item.Email);cell(row,text('Ուսանող','Student'));
        const statusLabel={Active:text('Ակտիվ','Active'),Suspended:text('Կասեցված','Suspended'),Banned:text('Արգելափակված','Banned')}[item.Status]||item.Status;
        cell(row,statusLabel+(item.IsEmailVerified?'':' · '+text('Չհաստատված','Unverified')));cell(row,item.LastLogin);
        const actions=cell(row,'');actions.className='actions-cell';actions.append(button(text('Փոփոխել','Edit'),()=>editUser(item)));
        actions.append(button(item.Status==='Active'?text('Կասեցնել','Suspend'):text('Ակտիվացնել','Activate'),async()=>{await api.save('/api/admin/users/'+item.UserID,'PUT',{FirstName:item.FirstName,LastName:item.LastName,GroupID:item.GroupID,Status:item.Status==='Active'?'Suspended':'Active'});await load();}));
      }else if(file.startsWith('ActivityLogs')){
        for(const value of [item.AdminID?'Admin #'+item.AdminID:item.UserID?'Student #'+item.UserID:'Anonymous / system',item.ActionType,item.Target,item.CreatedAt,item.Status])cell(row,value);
      }else{
        for(const value of [item.UserID?'Student #'+item.UserID:'Admin #'+item.AdminID,item.Email,item.CreatedAt,item.Purpose+' · '+(item.IsUsed?'Used':new Date(item.Expiry+'Z')<new Date()?'Expired':'Pending')])cell(row,value);
        cell(row,'').append(button(text('Կրկնել','Resend'),async()=>{const result=await api.save('/api/admin/password-resets','POST',{Email:item.Email,Role:item.AdminID?'admin':'student'});status.textContent=result.message;await load();}));
      }
      tbody.append(row);
    }
    if(!result.items.length){const row=document.createElement('tr');cell(row,text('Գրառումներ չկան','No records'));tbody.append(row);}
  }
  if(search&&!file.startsWith('ResetPassword')){search.onkeydown=async e=>{if(e.key==='Enter'){page=1;try{await load();}catch(error){report(error);}}};}
  if(file.startsWith('ResetPassword')){
    document.querySelector('.search-bar')?.remove();
    const info=document.querySelector('.info-content');if(info)info.textContent=text('Հղումը գործում է 30 րոպե՝ լռելյայն կարգավորմամբ։ Տեղային ռեժիմում իրական նամակ չի ուղարկվում։','Default link lifetime: 30 minutes. Local mode creates a private test message; no real email is sent.');
    const send=document.querySelector('.send-btn');if(send)send.onclick=async()=>{try{const result=await api.save('/api/admin/password-resets','POST',{Email:document.querySelector('.email-input input').value.trim(),Role:'student'});status.textContent=result.message;await load();}catch(e){report(e);}};
  }
  async function addRosterStudent(){
    const {modal,content}=accountDialog(text('Ուսանողի գրանցման թույլտվություն','Allow a student to register'));
    const form=document.createElement('form'),inputs={};
    for(const [key,label,type] of [['FirstName',text('Անուն','First name'),'text'],['LastName',text('Ազգանուն','Last name'),'text'],['Email',text('Համալսարանական էլփոստ','University email'),'email']]){
      const wrapper=document.createElement('label');wrapper.textContent=label;const input=document.createElement('input');input.type=type;input.required=true;input.maxLength=key==='Email'?255:100;wrapper.append(input);form.append(wrapper);inputs[key]=input;
    }
    const groupLabel=document.createElement('label');groupLabel.textContent=text('Հաստատված խումբ','Approved group');
    const groups=document.createElement('select');groups.required=true;groups.append(new Option(text('Ընտրեք խումբը','Choose group'),''));groupLabel.append(groups);form.append(groupLabel);
    const note=document.createElement('p');note.setAttribute('role','alert');form.append(note);
    const save=document.createElement('button');save.type='submit';save.textContent=text('Թույլատրել գրանցումը','Allow registration');save.disabled=true;
    form.append(save,button(text('Փակել','Close'),()=>modal.close()));content.append(form);document.body.append(modal);modal.onclose=()=>modal.remove();modal.showModal();
    try{
      for(let page=1;;page++){
        const result=await api.request('/api/admin/academic/groups?active=true&page_size=100&page='+page);
        for(const g of result.items)groups.append(new Option(g.GroupCode+' · '+g.EnrollmentYear,g.GroupID));
        if(page*result.page_size>=result.total)break;
      }save.disabled=false;
    }catch(e){note.textContent=e.message;}
    form.onsubmit=async event=>{event.preventDefault();save.disabled=true;try{
      await api.save('/api/admin/student-roster','POST',{FirstName:inputs.FirstName.value.trim(),LastName:inputs.LastName.value.trim(),Email:inputs.Email.value.trim(),GroupID:Number(groups.value)});
      modal.close();status.textContent=text('Ուսանողն ավելացված է թույլատրված ցանկում։ Այժմ կարող է գրանցվել իր էլփոստով։','Student added to the approved roster and can now register with that email.');
    }catch(e){note.textContent=e.message;}finally{save.disabled=false;}};
  }
  async function viewRoster(){
    const {modal,content}=accountDialog(text('Գրանցման թույլատրված ցանկ','Approved registration roster'),true);
    const explanation=document.createElement('p');explanation.textContent=text('Գրանցված ուսանողի ապաակտիվացումը նաև կասեցնում է նրա մուտքը։ Հաշիվը կրկին ակտիվացվում է Օգտատերերի ցանկից։','Deactivating a registered student also suspends sign-in. Reactivate the account from Users.');
    const search=document.createElement('input');search.placeholder=text('Անուն կամ էլփոստ','Name or email');search.setAttribute('aria-label',search.placeholder);
    const scope=document.createElement('select');scope.setAttribute('aria-label',text('Ցանկի տեսակը','Roster filter'));scope.append(new Option(text('Դեռ չգրանցվածներ','Not yet registered'),'pending'),new Option(text('Բոլորը','All students'),'all'));
    const table=document.createElement('table'),head=document.createElement('thead'),tr=document.createElement('tr'),body=document.createElement('tbody');
    for(const label of [text('Անուն','Name'),text('Էլփոստ','Email'),text('Խումբ','Group'),text('Հաշիվ','Account'),text('Գործողություն','Action')]){const th=document.createElement('th');th.textContent=label;tr.append(th);}head.append(tr);table.append(head,body);
    const note=document.createElement('p');note.setAttribute('role','alert');let rosterPage=1,total=0;
    async function refresh(){
      const result=await api.request('/api/admin/student-roster?page_size=20&page='+rosterPage+'&q='+encodeURIComponent(search.value||'')+(scope.value==='pending'?'&registered=false':''));total=result.total;body.replaceChildren();note.textContent=total?rosterPage+' / '+Math.max(1,Math.ceil(total/20)):text('Այս ցանկում ուսանողներ չկան։','No students in this list.');
      for(const item of result.items){const row=document.createElement('tr');cell(row,item.DisplayName||item.FirstName+' '+item.LastName);cell(row,item.Email);cell(row,item.GroupCode);cell(row,item.UserID?text('Գրանցված','Registered'):text('Սպասում է գրանցմանը','Not registered'));
        cell(row,'').append(button(item.IsActive?text('Ապաակտիվացնել','Deactivate'):text('Ակտիվացնել','Activate'),async()=>{
          try{await api.save('/api/admin/student-roster/'+encodeURIComponent(item.Email),'PUT',{IsActive:!item.IsActive});await refresh();}catch(e){note.textContent=e.message;}
        }));body.append(row);
      }
    }
    const run=async action=>{try{await action();}catch(e){note.textContent=e.message;}};
    scope.onchange=()=>run(async()=>{rosterPage=1;await refresh();});
    content.append(explanation,scope,search,button(text('Որոնել','Search'),()=>run(async()=>{rosterPage=1;await refresh();})),table,note,
      button('←',()=>run(async()=>{if(rosterPage>1){rosterPage--;await refresh();}})),button('→',()=>run(async()=>{if(rosterPage*20<total){rosterPage++;await refresh();}})),button(text('Փակել','Close'),()=>modal.close()));
    document.body.append(modal);modal.onclose=()=>modal.remove();modal.showModal();await run(refresh);
  }
  const add=document.querySelector('.add-user-btn');
  if(add){add.textContent=text('Գրանցման թույլտվություն','Allow registration');add.onclick=()=>addRosterStudent().catch(report);add.after(button(text('Թույլատրված ցանկ','Approved roster'),viewRoster));}
  const exportBtn=document.querySelector('.export-btn');
  if(exportBtn&&file.startsWith('users'))exportBtn.onclick=()=>api.download('/api/admin/users/export?page='+page+'&q='+encodeURIComponent(search?.value||''),'users.csv').catch(report);
  try{await load();}catch(e){report(e);}
})();