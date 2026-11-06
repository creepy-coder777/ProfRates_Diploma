(async()=>{const trText=ProfRatesI18n.t;const {el,show,run,button,form,pager,all,label}=S2;const api=ProfRatesAPI;
 const names={institutes:'Ինստիտուտներ',faculties:'Ֆակուլտետներ',chairs:'Ամբիոններ',specializations:'Մասնագիտացումներ',groups:'Խմբեր',courses:'Առարկաներ','student-courses':'Ուսանող–առարկա կապեր'};
 const keys={institutes:'InstituteID',faculties:'FacultyID',chairs:'ChairID',specializations:'SpecializationID',groups:'GroupID',courses:'CourseID','student-courses':'StudentCourseID'};
 const fields={institutes:{Name:'text',ShortName:'text',IsActive:'checkbox'},faculties:{Name:'text',ShortName:'text',IsActive:'checkbox'},chairs:{Name:'text',ShortName:'text',InstituteID:'number',FacultyID:'number',IsActive:'checkbox'},specializations:{Name:'text',Code:'text',ChairID:'number',IsActive:'checkbox'},groups:{GroupCode:'text',SpecializationID:'number',EnrollmentYear:'number',IsActive:'checkbox'},courses:{Name:'text',SpecializationID:'number',LecturerID:'number',CurriculumSemesterNumber:'number',IsActive:'checkbox'},'student-courses':{UserID:'number',CourseID:'number'}};
 const select=document.getElementById('s2Resource'),body=document.querySelector('tbody'),head=document.querySelector('thead tr');let current=1;
 for(const [v,t]of Object.entries(names))select.append(new Option(trText(t),v));select.value=new URLSearchParams(location.search).get('resource')||'institutes';if(!names[select.value])select.value='institutes';
 const params=new URLSearchParams(location.search);
 if(params.get('lecturer_id')){
  const back=el('a','action-btn',trText('Վերադառնալ դասախոսների ցանկին'),true);
  const fallback=ProfRatesI18n.page('professors_arm.html','professors.html');
  const raw=params.get('return_to');
  let target=fallback;
  if(raw){try{const url=new URL(raw,location.href);if(url.origin===location.origin&&/^\/frontend\/admin_portal\/professors(?:_arm)?\.html$/.test(url.pathname))target=url.pathname+url.search;}catch{}}
  back.href=target;document.querySelector('.section-header').prepend(back);
 }
 const search=document.querySelector('.search-bar input');const pages=pager(load);document.querySelector('table').after(pages.node);
 const path=()=>select.value==='student-courses'?'/api/admin/student-courses':'/api/admin/academic/'+select.value;
 const query=()=>new URLSearchParams({page:current,page_size:20,q:search.value,...(select.value==='courses'&&new URLSearchParams(location.search).get('lecturer_id')?{lecturer_id:new URLSearchParams(location.search).get('lecturer_id')}:{})});
 async function optionsFor(resource){const opts={};const source={InstituteID:'institutes',FacultyID:'faculties',ChairID:'chairs',SpecializationID:'specializations',LecturerID:'lecturers',CourseID:'courses',UserID:'student-options',CurriculumSemesterNumber:'semesters'};
  for(const key of Object.keys(fields[resource]))if(source[key]){const s=source[key];const path=['lecturers','student-options','semesters'].includes(s)?'/api/admin/'+s:'/api/admin/academic/'+s;
   const rows=await all(path);opts[key]=rows.map(r=>({value:r[key==='CurriculumSemesterNumber'?'SemesterNumber':key],label:r.Name||r.NameHy||[r.FirstName,r.LastName].filter(Boolean).join(' ')||String(r[key])}));}
  return opts;
 }
 async function edit(item={}){const r=select.value;const base=path();const key=keys[r];const initial={...item};
  if(r==='courses'&&!item[key]){const lecturer=new URLSearchParams(location.search).get('lecturer_id');if(lecturer)initial.LecturerID=Number(lecturer);}
  await form(names[r],fields[r],initial,async payload=>{await api.save(base+(item[key]?'/'+item[key]:''),item[key]?'PUT':'POST',payload);await load(current);},await optionsFor(r));}
 async function load(page=1){current=page;body.replaceChildren();head.replaceChildren();const r=select.value;const data=await api.request(path()+'?'+query());
  const columns=r==='student-courses'?['StudentCourseID','UserID','StudentFirstName','StudentLastName','GroupCode','CourseID','CourseName','EnrolledAt']:[keys[r],...Object.keys(fields[r])];for(const c of columns)head.append(el('th','',label[c]||c));head.append(el('th','','Գործողություններ'));
  for(const row of data.items){const tr=el('tr');for(const c of columns)tr.append(el('td','',typeof row[c]==='boolean'?(row[c]?'Ակտիվ':'Պասիվ'):row[c]??'—',typeof row[c]!=='boolean'));
   const td=el('td');if(r!=='student-courses')td.append(button('Խմբագրել',()=>edit(row)));
   if(r==='student-courses'||row.IsActive)td.append(button(r==='student-courses'?'Հեռացնել կապը':'Ապաակտիվացնել',async()=>{if(confirm(trText('Կատարե՞լ գործողությունը։'))){await api.request(path()+'/'+row[keys[r]],{method:'DELETE'});await load(current);}}));
   tr.append(td);body.append(tr);
  }pages.update(data);show(r==='courses'?'Դասախոս–առարկա կապը փոխվում է առարկայի «Դասախոս» դաշտով։':r==='student-courses'?'Կապի հեռացումը չի ջնջում նախկին գնահատումները։':'');
 }
 select.onchange=()=>run(()=>load(1));document.querySelector('.add-professor-btn').onclick=()=>run(()=>edit());
 document.querySelector('.export-btn').onclick=()=>run(()=>api.download(path()+'/export?'+query(),select.value+'-page-'+current+'.csv'));
 search.oninput=()=>{clearTimeout(search.timer);search.timer=setTimeout(()=>run(()=>load(1)),300);};await run(load);
})();
