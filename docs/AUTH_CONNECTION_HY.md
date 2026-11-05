# Առաջին ուսանողի նույնականացման միացման կոնկրետ քայլերը

## Ինչ է պետք առաջին մասնակցից

Նրա FastAPI-ի մուտքի router-ը, token/session ստուգող գործառույթը կամ middleware-ը, ստուգված ինքնության ձևաչափը և Admins.AdminID-ի ստացման կանոնը։ Cookie-ի դեպքում պետք է հայտնի լինեն cookie-ի անունը, SameSite/Secure կարգավորումները և CSRF մեխանիզմը։ Գաղտնի JWT բանալիները, գաղտնաբառերը և իրական session-ները զրույցում պետք չեն։

## 1. Միավորել նույն FastAPI հավելվածում

Միացրեք առաջին մասնակցի իրական login/logout router-ը `app/main.py`-ի `app`-ին՝ նրա իրական module-ի `router`-ով։ Օգտագործեք նույն բազայի տեղային կարգավորումները։ Router-ի module անունն այստեղ չի հորինվում. այն պետք է վերցնել նրա նախագծից։

## 2. Իրական ստուգումից ստանալ Principal

Առաջին բաժնի ծառայությունը պետք է ստուգի token-ի ստորագրությունն ու ժամկետը կամ server-side session-ը, հաշվի գործող կարգավիճակը, իրավունքն ու AdminID-ն։ Դրանից հետո կան երկու եղանակ։

Ա. Նրա համաժամանակյա `Request -> Principal` adapter-ի իրական ուղին գրեք `.env`-ի `AUTH_PROVIDER=module:function` դաշտում։ `Principal`-ը ներմուծվում է `app.security`-ից։

Բ. Եթե նույնականացումը middleware-ով է, իրական ստուգումից հետո middleware-ը միայն սերվերի վրա ստեղծում է՝

```python
from app.security import Principal

# verified_* արժեքները գալիս են առաջին մասնակցի իրական ստուգման արդյունքից։
request.state.verified_profrates_principal = Principal(
    user_id=verified_user_id,
    is_admin=verified_is_admin,
    admin_id=verified_admin_id,
)
```

Այնուհետև `.env`-ում՝

```dotenv
AUTH_PROVIDER=app.integrations.first_student:resolve_principal
```

Այս bridge-ը փաթեթում կա։ Այն ինքնուրույն token չի հաստատում. առանց middleware-ի ստեղծած ստուգված Principal-ի միշտ վերադարձնում է 401։ Չստուգված `X-Role`, `X-Admin-ID`, body կամ token payload-ից արժեքներ վերցնելը չի թույլատրվում։ AdminID-ն առանձին `Admins` աղյուսակի ID-ն է. այն UserID-ի հետ նույնացնել չի կարելի։ `get_actor`-ը բազայում ստուգում է այդ AdminID-ի գոյությունը։

Եթե առաջին մասնակցի ստուգիչը async dependency է, նա պետք է այն կանչի իր իրական async middleware/adapter-ում և հետո գրի վերը նշված trusted state-ը։ Մեր `AUTH_PROVIDER`-ի ընթացիկ ուղիղ contract-ը համաժամանակյա է։

## 3. Frontend-ից փոխանցել իրական credential-ը

Սովորական նույն origin-ի cookie session-ն ուղարկվում է ինքնաբերաբար։ Եթե պահանջվում է Bearer կամ CSRF header, առաջին մասնակցի իրական login կոդից հետո և `student2_*.js`-ից առաջ սահմանվում է՝

```javascript
window.ProfRatesAuth = {
  async getHeaders() {
    // Վերադարձնել ձեր իրական session համակարգի պահանջած header-ները։
    // Օրինակ՝ Authorization կամ X-CSRF-Token, եթե այդպես է նախագծված։
    return headersFromYourVerifiedLogin;
  }
};
```

Սա պայմանագրի օրինակ է, ոչ աշխատող login իրականացում։ Header-ների արժեքները կամ token-ի պահպանումը պետք է տա առաջին բաժինը։ Կոդում մշտական token մի գրեք։ Login-ից հետո նույն browser-ի նույն origin-ում բացեք ադմինի էջը։ Անգլերեն էջերը նույն credential մեխանիզմն են օգտագործում։

## 4. Վերագործարկել և ստուգել

Վերագործարկեք uvicorn-ը `.env`-ի փոփոխությունից հետո։ `tools.check_auth`-ով կամ browser Network-ով ստուգեք՝ anonymous 401, forged token/role 401, իրական ադմին 200, իրական ուսանող՝ ադմին գործողության համար 403։

```powershell
.venv\Scripts\python.exe -m tools.check_auth --mode token
```

Cookie-ի դեպքում՝ `--mode cookie`։ Մուտքը թաքնված է և միայն տեղային է։ Գործիքը գրում է միայն HTTP status-ները `exports/auth_check.json`-ում, ոչ credential-ը։ Այն ոչ մի բազային փոփոխություն չի կատարում։

Այնուհետև իրական մուտքով UI-ում կատարեք `docs/LOCAL_MSSQL_CHECKS_HY.md`-ի պահպանման քայլերը։ Սերվերի նույնականացման module-ի բացակայությամբ այս փուլը դեռ չփորձարկված է. testclient-ի ադմին override-ը չի համարվում թիմային միացում և production-ում չի միացվում։

## 5. Audit

Լռելյայն օգտագործվում է առկա ActivityLogs-ը՝ նույն transaction-ում։ Առաջին բաժնի ընդհանուր audit ծառայությունն առկա լինելու դեպքում միացրեք նրա իրական `AUDIT_PROVIDER=module:function` callback-ը։ Այն պետք է ընդունի `(db_connection, principal, action, target)` և օգտագործի տրված transaction-ը՝ առանց առանձին commit-ի կամ կրկնակի գրանցման։ Trigger-ով audit-ի դեպքում նախ ուսումնասիրեք trigger-ը, որպեսզի նույն գործողությունը երկու անգամ չգրանցվի։
