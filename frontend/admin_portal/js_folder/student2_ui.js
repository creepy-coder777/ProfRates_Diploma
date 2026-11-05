window.S2 = (()=>{const trText=ProfRatesI18n.t;
 const el=(tag,cls,text,raw=false)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=raw?String(text):trText(text);return n;};
 const message=el('p','','');message.setAttribute('role','status');message.setAttribute('aria-live','polite');
 const host=document.querySelector('.main-content')||document.querySelector('main')||document.body;host.prepend(message);
 const show=e=>{message.textContent=e instanceof Error?ProfRatesI18n.error(e.message):trText(e);};
 const run=async f=>{try{return await f();}catch(e){show(e);return undefined;}};
 const button=(text,fn,cls='action-btn')=>{const b=el('button',cls,text);b.type='button';b.onclick=()=>run(fn);return b;};
 const all=async path=>{let items=[],page=1;while(true){const b=await ProfRatesAPI.request(path+(path.includes('?')?'&':'?')+'page_size=100&page='+page);items.push(...b.items);if(!b.total||items.length>=b.total)break;page++;}return items;};
 const label={StudentFirstName:'Անուն',StudentLastName:'Ազգանուն',CourseName:'Առարկա',EnrolledAt:'EnrolledAt',StudentCourseID:'StudentCourseID',FirstName:'Անուն',MiddleName:'Հայրանուն',LastName:'Ազգանուն',Title:'Կոչում',PhotoUrl:'Նկարի հասցե',Description:'Նկարագրություն',IsActive:'Ակտիվ',Name:'Անվանում',ShortName:'Կրճատ անվանում',InstituteID:'Ինստիտուտ',FacultyID:'Ֆակուլտետ',ChairID:'Ամբիոն',SpecializationID:'Մասնագիտացում',GroupCode:'Խմբի կոդ',EnrollmentYear:'Ընդունման տարի',Code:'Կոդ',LecturerID:'Դասախոս',CurriculumSemesterNumber:'Ուսումնական կիսամյակ',Text:'Հարց',Category:'Բաժին',SortOrder:'Հերթականություն',UserID:'Ուսանող',CourseID:'Առարկա'};
 async function form(title,fields,initial,onSave,options={}){
  const dialog=el('dialog','admin-dialog');
  dialog.append(el('h2','',trText(title)));const f=el('form');const inputs={};
  for(const [key,type] of Object.entries(fields)){
   const l=el('label','',label[key]||key);l.style.display='block';l.style.marginTop='10px';let n;
   if(options[key]){n=el('select');n.append(new Option(trText('Ընտրել…'),''));for(const item of options[key])n.append(new Option(item.label,String(item.value)));}
   else if(type==='textArea')n=el('textarea');else {n=el('input');n.type=type;}
   n.style.cssText='width:100%;padding:9px;border:1px solid #ccc;border-radius:8px';
   if(type==='checkbox'){n.checked=initial[key]??true;n.style.width='auto';}else n.value=initial[key]??'';
   l.append(n);f.append(l);inputs[key]=[n,type];
  }
  const error=el('p');error.setAttribute('role','alert');f.append(error);
  const actions=el('div','admin-dialog-actions');
  const save=el('button','add-professor-btn','Պահպանել');save.type='submit';actions.append(save);
  actions.append(button('Չեղարկել',()=>dialog.close()));f.append(actions);
  f.onsubmit=async e=>{e.preventDefault();save.disabled=true;const body={};
   for(const [k,[n,type]] of Object.entries(inputs))body[k]=type==='checkbox'?n.checked:type==='number'?(n.value===''?null:Number(n.value)):n.value.trim()||null;
   try{await onSave(body);dialog.close();}catch(e){error.textContent=ProfRatesI18n.error(e.message);}finally{save.disabled=false;}
  };
  dialog.append(f);document.body.append(dialog);dialog.addEventListener('close',()=>dialog.remove());dialog.showModal();
 }
 function pager(load){let current=1;const node=el('div','pagination');const txt=el('span');const prev=button('Նախորդ',()=>load(current-1));const next=button('Հաջորդ',()=>load(current+1));node.append(prev,txt,next);return {node,update(data){current=data.page;txt.textContent=' '+trText('{page} էջ · {total} գրառում',{page:current,total:data.total})+' ';prev.disabled=current<=1;next.disabled=current*data.page_size>=data.total;}};}
 return {el,show,run,button,all,label,form,pager};
})();
