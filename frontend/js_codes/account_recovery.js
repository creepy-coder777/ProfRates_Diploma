(() => {
  const page=document.querySelector('[data-recovery-role]');if(!page)return;
  const role=page.dataset.recoveryRole,language=page.dataset.recoveryLanguage;
  const english=language==='en',text=(hy,en)=>english?en:hy;
  const params=new URLSearchParams(location.hash.slice(1));
  let token=params.get('token'),verifying=params.get('purpose')==='verify';
  history.replaceState(null,'',location.pathname+location.search);
  const status=document.getElementById('status'),requestForm=document.getElementById('request-form');
  const tokenForm=document.getElementById('token-form'),codeForm=document.getElementById('code-form');
  const passwordFields=document.getElementById('password-fields'),password=document.getElementById('new-password');
  const confirmation=document.getElementById('confirm-password'),tokenButton=tokenForm.querySelector('[type=submit]');
  const email=document.getElementById('email'),code=document.getElementById('reset-code');
  const payload=()=>({Email:email.value.trim(),Language:language});
  function errorMessage(e){
    if(e.status===400)return text('Կոդը կամ հղումը սխալ է, ժամկետանց է կամ արդեն օգտագործվել է։','The code or link is invalid, expired, or already used.');
    if(e.status===429)return text('Չափազանց շատ փորձեր են կատարվել։ Փորձեք ավելի ուշ։','Too many attempts. Please try again later.');
    if(e.status===422)return text('Ստուգեք մուտքագրված տվյալները։ Կոդը պետք է լինի 6 թվանշան։','Check your details. The code must contain 6 digits.');
    return e.message||text('Հարցումը չհաջողվեց։','The request failed.');
  }
  async function submit(button,action){button.disabled=true;status.textContent='';try{await action();}catch(e){status.textContent=errorMessage(e);}finally{button.disabled=false;}}
  function showTokenForm(){
    requestForm.hidden=true;codeForm.hidden=true;tokenForm.hidden=false;
    document.getElementById('purpose').textContent=verifying?text('Հաստատեք ձեր էլ․ հասցեն։','Verify your email address.'):text('Սահմանեք նոր գաղտնաբառ։','Set a new password.');
    passwordFields.hidden=verifying;password.required=confirmation.required=!verifying;
    tokenButton.textContent=verifying?text('Հաստատել էլ․ հասցեն','Verify email'):text('Փոխել գաղտնաբառը','Change password');
  }
  requestForm.addEventListener('submit',event=>{
    event.preventDefault();const button=event.submitter||requestForm.querySelector('[type=submit]');
    submit(button,async()=>{
      const result=await ProfRatesAPI.save(`/api/auth/${role}/password-code`,'POST',payload());
      token=null;verifying=false;tokenForm.hidden=true;requestForm.hidden=true;codeForm.hidden=false;
      code.value='';code.focus();status.textContent=result.message;
    });
  });
  codeForm.addEventListener('submit',event=>{
    event.preventDefault();const button=event.submitter||codeForm.querySelector('[type=submit]');
    submit(button,async()=>{
      const result=await ProfRatesAPI.save(`/api/auth/${role}/verify-password-code`,'POST',{...payload(),Code:code.value.trim()});
      token=result.Token;verifying=false;code.value='';showTokenForm();password.focus();
      status.textContent=text('Կոդը հաստատված է։ Մուտքագրեք նոր գաղտնաբառը։','Code verified. Enter your new password.');
    });
  });
  document.getElementById('code-back').onclick=()=>{token=null;code.value='';codeForm.hidden=true;tokenForm.hidden=true;requestForm.hidden=false;status.textContent='';email.focus();};
  const resend=document.getElementById('resend');
  if(resend&&role==='student')resend.onclick=()=>{
    if(!requestForm.reportValidity())return;
    submit(resend,async()=>{const result=await ProfRatesAPI.save('/api/auth/student/resend-verification','POST',payload());status.textContent=result.message;});
  };
  tokenForm.addEventListener('submit',event=>{
    event.preventDefault();
    if(!token){status.textContent=text('Նախ հաստատեք վերականգնման կոդը։','Verify the reset code first.');return;}
    if(!verifying&&password.value!==confirmation.value){status.textContent=text('Գաղտնաբառերը չեն համընկնում։','The passwords do not match.');confirmation.focus();return;}
    submit(tokenButton,async()=>{
      const endpoint=verifying?'/api/auth/verify-email':`/api/auth/${role}/reset-password`;
      await ProfRatesAPI.save(endpoint,'POST',{Token:token,...(!verifying?{Password:password.value}:{})});
      tokenForm.hidden=true;password.value=confirmation.value='';token=null;
      status.textContent=verifying?text('Էլ․ հասցեն հաստատված է։ Այժմ կարող եք մուտք գործել։','Email verified. You can now sign in.'):text('Գաղտնաբառը փոխված է։ Մուտք գործեք նոր գաղտնաբառով։','Password changed. Sign in with your new password.');
    });
  });
  if(token){
    if(!['verify','reset'].includes(params.get('purpose'))){status.textContent=text('Հղման նպատակը վավեր չէ։','Invalid link purpose.');token=null;return;}
    showTokenForm();
  }
})();
