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
      const labels=document.querySelectorAll('.stat-label');if(labels[3])labels[3].textContent=text('Հաստատված գնահատումների միջին','Average of approved ratings');
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
  const filters={};
  async function allOptions(path){
    const items=[];
    for(let n=1;;n++){
      const result=await api.request(path+(path.includes('?')?'&':'?')+'page_size=100&page='+n);
      items.push(...result.items);if(n*result.page_size>=result.total)return items;
    }
  }
  function userQuery(){const params=new URLSearchParams({page:String(page),page_size:'20',q:search?.value||'',lang:en?'en':'hy'});
    for(const [key,input]of Object.entries(filters))if(input.value)params.set(key,input.value);return params;}
  if(file.startsWith('users')){
    const bar=document.createElement('div');bar.className='student-filter-bar';
    const specs=[['institute_id',text('Բոլոր ինստիտուտները','All institutes'),'institutes','InstituteID','Name'],['faculty_id',text('Բոլոր ֆակուլտետները','All faculties'),'faculties','FacultyID','Name'],['chair_id',text('Բոլոր ամբիոնները','All chairs'),'chairs','ChairID','Name'],['specialization_id',text('Բոլոր մասնագիտությունները','All specializations'),'specializations','SpecializationID','Name'],['group_id',text('Բոլոր խմբերը','All groups'),'groups','GroupID','GroupCode']];
    for(const [key,title]of [...specs,['year',text('Բոլոր կուրսերը','All study years')],['status',text('Բոլոր կարգավիճակները','All statuses')]]){
      const select=document.createElement('select');select.setAttribute('aria-label',title);select.append(new Option(title,''));filters[key]=select;bar.append(select);
      select.onchange=async()=>{page=1;try{await load();}catch(e){report(e);}};
    }
    for(let n=1;n<=4;n++)filters.year.append(new Option(text(n+'-րդ կուրս','Year '+n),n));
    for(const [value,title]of [['Active',text('Ակտիվ','Active')],['Suspended',text('Կասեցված','Suspended')],['Banned',text('Արգելափակված','Banned')]])filters.status.append(new Option(title,value));
    document.querySelector('.section-header').after(bar);
    const headers=table.querySelector('thead tr');headers.replaceChildren();
    for(const title of [text('Անուն','Name'),text('Էլփոստ','Email'),text('Խումբ','Group'),text('Մասնագիտություն','Specialization'),text('Կուրս','Year'),text('Կարգավիճակ','Status'),text('Վերջին մուտք','Last login'),text('Գործողություններ','Actions')]){const th=document.createElement('th');th.textContent=title;headers.append(th);}
    try{await Promise.all(specs.map(async([key,title,resource,id,name])=>{
      for(const item of await allOptions('/api/admin/academic/'+resource))filters[key].append(new Option(item[name],item[id]));
    }));}catch(e){report(e);}
  }
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
    const url=file.startsWith('users')?endpoint+'?'+userQuery():endpoint+'?page='+page+'&page_size=20'+(!file.startsWith('ResetPassword')?'&q='+encodeURIComponent(search?.value||''):'');
    const result=await api.request(url);total=result.total;tbody.replaceChildren();pageNote.textContent=' '+page+' / '+Math.max(1,Math.ceil(total/20))+' ';
    for(const item of result.items){
      const row=document.createElement('tr');
      if(file.startsWith('users')){
        cell(row,item.DisplayName||item.FirstName+' '+item.LastName);cell(row,item.Email);cell(row,item.GroupCode);cell(row,item.SpecializationName);cell(row,item.StudyYear??text('Չսահմանված','Not configured'));
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
    const send=document.querySelector('.send-btn');if(send)send.onclick=async()=>{const email=document.querySelector('.email-input input');if(!email.reportValidity())return;send.disabled=true;try{const result=await api.save('/api/admin/password-resets','POST',{Email:email.value.trim(),Role:'student'});await load();status.textContent=result.message;}catch(e){report(e);}finally{send.disabled=false;}};
  }
  async function addStudent(){
    const {modal,content}=accountDialog(text('Ավելացնել ուսանողի հաշիվ','Add student account'));
    const form=document.createElement('form'),inputs={};
    for(const [key,label,type] of [['FirstName',text('Անուն','First name'),'text'],['LastName',text('Ազգանուն','Last name'),'text'],['Email',text('Համալսարանական էլփոստ','University email'),'email'],['Password',text('Նախնական գաղտնաբառ (առնվազն 12 նիշ)','Initial password (at least 12 characters)'),'password'],['ConfirmPassword',text('Կրկնել գաղտնաբառը','Confirm password'),'password']]){
      const wrapper=document.createElement('label');wrapper.textContent=label;
      const input=document.createElement('input');input.name=key;input.type=type;input.required=true;
      input.maxLength=key==='Email'?255:type==='password'?128:100;
      if(type==='password'){input.minLength=12;input.autocomplete='new-password';}
      if(key==='Email'){input.autocomplete='off';input.pattern='[^@\\s]+@[Pp][Oo][Ll][Yy][Tt][Ee][Cc][Hh][Nn][Ii][Cc]\\.[Aa][Mm]';}
      wrapper.append(input);form.append(wrapper);inputs[key]=input;
    }
    const label=document.createElement('label');label.textContent=text('Խումբ','Group');
    const groups=document.createElement('select');groups.required=true;groups.append(new Option(text('Ընտրեք խումբը','Choose group'),''));label.append(groups);form.append(label);
    const explanation=document.createElement('p');explanation.textContent=text('Հաշիվը ստեղծվելու է անմիջապես։ Գաղտնաբառը փոխանցեք ուսանողին անձնական անվտանգ եղանակով։','The account will be ready to sign in. Deliver its initial password privately.');form.append(explanation);
    const note=document.createElement('p');note.setAttribute('role','alert');form.append(note);
    const save=document.createElement('button');save.type='submit';save.textContent=text('Ստեղծել հաշիվ','Create account');save.disabled=true;
    form.append(save,button(text('Փակել','Close'),()=>modal.close()));content.append(form);document.body.append(modal);modal.showModal();
    try{
      const [allGroups,specializations]=await Promise.all([allOptions('/api/admin/academic/groups?active=true'),allOptions('/api/admin/academic/specializations?active=true')]);
      const names=new Map(specializations.map(x=>[x.SpecializationID,x.Name]));
      for(const g of allGroups)groups.append(new Option([g.GroupCode,names.get(g.SpecializationID),g.EnrollmentYear].filter(Boolean).join(' · '),g.GroupID));
      save.disabled=!allGroups.length;
      if(!allGroups.length)note.textContent=text('Ակտիվ խմբեր չկան։ Նախ լրացրեք ուսումնական տվյալները։','No active groups. Configure academic data first.');
    }catch(e){note.textContent=e.message;}
    form.onsubmit=async event=>{event.preventDefault();
      if(!form.reportValidity())return;
      if(inputs.Password.value!==inputs.ConfirmPassword.value){note.textContent=text('Գաղտնաբառերը չեն համընկնում։','Passwords do not match.');return;}
      save.disabled=true;note.textContent='';
      try{
        const result=await api.save('/api/admin/users','POST',{FirstName:inputs.FirstName.value.trim(),LastName:inputs.LastName.value.trim(),Email:inputs.Email.value.trim(),Password:inputs.Password.value,GroupID:Number(groups.value)});
        inputs.Password.value=inputs.ConfirmPassword.value='';modal.close();page=1;await load();
        status.textContent=text('Ուսանողի հաշիվը ստեղծված է։','Student account created.')+' '+academicMessage(result.academic_status);
      }catch(e){note.textContent=e.message;}finally{save.disabled=false;}
    };
  }
  function academicMessage(value){
    if(value==='ready')return text('Ուսումնական կապերը պատրաստ են։','Academic links are ready.');
    const messages={
      'curriculum-missing':text('Ընթացիկ կիսամյակի ակտիվ առարկաներ/դասախոսներ չկան։ Գնահատումը դեռ հասանելի չէ։','No active courses/lecturers for the current semester. Rating is not yet available.'),
      'term-unconfigured':text('Ընթացիկ ուսումնական շրջանը կարգավորված չէ։','The current academic term is not configured.'),
      'semester-unconfigured':text('Կիսամյակի տվյալը բացակայում է։','The academic semester is not configured.'),
      'academic-review-required':text('Ընդունելության տարին կամ կիսամյակը պահանջում է ստուգում։','Enrollment year or semester requires review.'),
      'group-unavailable':text('Խմբի ուսումնական տվյալները հասանելի չեն։','The group academic data is unavailable.')};
    return messages[value]||text('Ստուգեք ուսումնական կապերը։','Check academic links.');
  }
  const add=document.querySelector('.add-user-btn');
  if(add){add.textContent=text('Ավելացնել ուսանող','Add student');add.onclick=()=>addStudent().catch(report);}
  const exportBtn=document.querySelector('.export-btn');
  if(exportBtn&&file.startsWith('users'))exportBtn.onclick=()=>api.download('/api/admin/users/export?'+userQuery(),'users.csv').catch(report);
  try{await load();}catch(e){report(e);}
})();