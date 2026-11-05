# Երեք բաժինների միավորման պայմանագիր

## script.sql արտահանմամբ հաստատված կառուցվածքային փաստեր

Հիմք՝ 21.10.2026-ին արտահանված `script.sql`, բազա՝ `ProfRates_databaza`։ Արտահանման CREATE/ALTER/INSERT հրամանները չեն կատարվել։ Mapping-ը ստացվել է CREATE TABLE բաժիններից. տվյալների և գաղտնի արժեքների պատճեններ փաթեթի մեջ չեն ներառվել։

| Հայեցակարգ | Իրական պահպանում |
| --- | --- |
| Դասախոս | `dbo.Lecturers`՝ FirstName/MiddleName/LastName, Title, PhotoUrl, Description, IsActive |
| Ինստիտուտ / ֆակուլտետ | `dbo.Institutes` / `dbo.Faculty`՝ իրար կապող FK չկա |
| Ամբիոն | `dbo.Chairs`՝ InstituteID ԿԱՄ FacultyID, XOR սահմանափակում |
| Մասնագիտացում | `dbo.Specializations.ChairID` |
| Խումբ | `dbo.StudentGroups.SpecializationID`, EnrollmentYear |
| Առարկա և դասախոս | `dbo.Courses.LecturerID`, SpecializationID, CurriculumSemesterNumber |
| Ուսանող–առարկա | `dbo.StudentCourses.UserID`, CourseID |
| Հարցեր | `dbo.Questions`՝ Text, Category, SortOrder, IsActive |
| Նախկին պատասխան | `dbo.RatingAnswers.QuestionID` |
| Մոդերացիա | `dbo.Ratings.Status`, ApprovedByAdminID, UpdatedAt |
| Ամփոփում | `dbo.vwLecturerRatingSummary`՝ հաստատված գնահատումների live view |
| Անանուն հրապարակում | `dbo.vw_Ratings_Public`՝ Approved ֆիլտրով, առանց ուսանողի անձնական դաշտերի |
| Ադմին և audit | `dbo.Admins`, `dbo.ActivityLogs` |

Արտահանված հարցաշարում 6 ակտիվ հարց է։ Գործող բազայում թիվը կարող է փոխված լինել. երկու էջերն օգտագործում են ընթացիկ նույն աղբյուրը։

## Առաջին ուսանողին

Նա իրականացնում է գրանցումը, login/logout-ը, էլփոստի հաստատումը, գաղտնաբառի վերականգնումը և իրավունքների ստուգումը։ Այս փաթեթում դրանք չկան։

Մեր սերվերը կանչում է `.env`-ի `AUTH_PROVIDER=module:function` համաժամանակյա adapter-ը՝ մեկ `fastapi.Request` պարամետրով։ Այն պետք է ինքնուրույն ստուգի session/JWT-ի ստորագրությունը, ժամկետը, հաշվի գործող կարգավիճակը և իրավունքները։ Արդյունքը՝

```python
from app.security import Principal

# Միայն արդեն ստուգված ինքնությունից ստացված արժեքներ։
# AdminID-ն Admins աղյուսակի բանալին է, ոչ UserID-ն։
return Principal(user_id=verified_user_id, is_admin=verified_is_admin,
                 admin_id=verified_admin_id)
```

Վերը contract-ի return-ն է, ոչ ինքնուրույն login գործառույթ։ Adapter-ը մուտքի բացակայության դեպքում պետք է նետի HTTPException(401), արգելված դերի դեպքում՝ 403։ Այն չպետք է վերցնի is_admin կամ admin_id-ն չստուգված request header/body-ից։ Admin-ի համար user_id-ն կարող է լինել None, քանի որ Admins-ը Users-ից առանձին է։

`AUTH_PROVIDER`-ը դատարկ լինելու դեպքում՝ 401։ Adapter-ի սխալի դեպքում՝ 503։ `require_admin`-ը ստուգում է դերը, `get_actor`-ը՝ իրական AdminID-ի առկայությունը բազայում։ Adմինի փոփոխող հարցումները մերժվում են, եթե ուղարկված Origin-ը սերվերի origin-ից տարբեր է։ Cookie-ով նույնականացման ամբողջական CSRF/session քաղաքականությունն առաջին բաժնի պատասխանատվությունն է։

Frontend-ի `ProfRatesAPI`-ն օգտագործում է same-origin cookies։ Եթե անհրաժեշտ է Bearer կամ CSRF header, առաջին բաժինը մինչև էջի գործարար script-երը տրամադրում է `window.ProfRatesAuth.getHeaders()` ֆունկցիան։ Այն վերադարձնում է header-ների օբյեկտը։ Token-ի պահպանում այս բաժինը չի սահմանում։

### Audit-ի մեկ ընդհանուր կետ

Լռելյայն երկրորդ բաժինը նույն transaction-ում մեկ գրառում է ավելացնում առկա `ActivityLogs`-ում՝ AdminID-ով։ Սա ընդհանուր մատյանի օգտագործում է, ոչ առաջին բաժնի մատյանի կառավարման կրկնօրինակում։

Եթե առաջին բաժինը տրամադրում է ընդհանուր audit ծառայություն, դրեք `AUDIT_PROVIDER=team_audit.service:record`։ Այդ համաժամանակյա ֆունկցիայի signature-ը՝ `record(db_connection, principal, action, target)`։ Այն օգտագործում է տրված connection-ը, չի կատարում առանձին commit և չի կրկնում գործողությունը։ Արտաքին provider ունենալիս տեղային INSERT չի կատարվում։ Եթե provider-ը ձախողվի, հիմնական գործողությունն էլ հետ է գլորվում։ Եթե audit-ը կատարվում է առկա DB trigger-ով, նախ ստուգել դրա սահմանումը և համաձայնեցնել նույն callback-ի համապատասխան իրականացումը։

## Երրորդ ուսանողին

Այս փաթեթը չի ստեղծում, փոխում կամ ջնջում ուսանողի գնահատումները, չի ստուգում նրա գնահատելու իրավունքը, չի իրականացնում հավանումներ կամ Bayesian հաշվարկ։

Գնահատման էջը բեռնում է `/api/questions`-ի ակտիվ հարցերը՝ իրական QuestionID-ներով։ Պատասխանները չեն համարվում հաստատված կամ պահպանված, մինչև երրորդ բաժնի ծառայությունը հաջողությամբ չավարտվի։ Նրա Frontend adapter-ը՝

```javascript
window.ProfRatesRatings = {
  async submit(payload) {
    // Կանչել ձեր իրական պաշտպանված գնահատման API-ն։
    // Անհաջողության դեպքում throw Error(...), հաջողության դեպքում return արդյունքը։
  }
};
```

`payload`-ը ներառում է LecturerID, CourseID, TermID, Comment և `answers: [{QuestionID, Score}]`։ Սա JavaScript ինտեգրման պայմանագիր է, ոչ բազայի նոր դաշտ։ Երրորդ բաժնի adapter-ը կարող է վերաձևավորել payload-ը իր API-ի համար։ LecturerID/CourseID/TermID համատեքստը գալիս է URL-ի `lecturer_id`, `course_id`, `term_id` պարամետրերից. դրանց ընտրության էջը երրորդ բաժինն է տրամադրում։ Միայն LecturerID ունենալը բավարար չէ գնահատում ուղարկելու համար։

Երրորդ բաժինը պարտավոր է ստուգել՝ իրական ուսանողն իրավունք ունի գնահատելու առարկայի դասախոսին, հարցերը դեռ ակտիվ են, պատասխանները ամբողջական են, և չկան կրկնվող գնահատումներ/պատասխաններ։ Ստուգումն ու պահպանումը պետք է լինեն մեկ transaction-ում, որովհետև ադմինը կարող է հարցաշարը փոխել բացված ձևի ընթացքում։

### Մոդերացիայի ազդեցությունը

`Ratings`-ում մեկ Status կա ամբողջ գնահատման համար՝ Pending/Approved/Rejected։ Հետևաբար հաստատումն ու մերժումը վերաբերում են նաև դրա վարկանիշում ընդգրկվելուն, ոչ միայն Comment տեքստին։ Frontend-ը սա բացատրում է հաստատման պատուհանում։ Բազայի փոփոխություն չի պահանջվել և չի կատարվել։

Մոդերացիան ընդունում է `status` և `expected_status`՝ զուգահեռ խմբագրումը հայտնաբերելու համար։ Նույն կարգավիճակի կրկնվող հաստատումը նոր audit կամ վերահաշվարկ չի ստեղծում։ Սխալ հին կարգավիճակի դեպքում վերադարձվում է 409։

`vwRatingScores` և `vwLecturerRatingSummary`-ը live հաշվարկներ են. կարգավիճակի փոփոխությունից հետո արդյունքը փոխվում է view-ի հաջորդ ընթերցման ժամանակ։ Python-ում հաշվարկ/ամփոփման INSERT/UPDATE/հաշվարկային procedure-ի կանչ չկա։ `uspLecturerRankings`-ի Bayesian տրամաբանությունը չի կրկնվում։ Եթե երրորդ բաժինն ունի առանձին cache, այն պետք է թարմացվի հաջող commit-ից հետո կամ չօգտագործվի այս live view-երի ընթերցման ուղու համար։ Առանձին cache այս փաթեթում չկա։

## Տեղային միացումից հետո անհրաժեշտ ապացույցներ

`tools.verify_schema`-ի արդյունքը, իսկ սխալի դեպքում՝ HTTP status-ը և գաղտնի տվյալներ չպարունակող սխալի հաղորդագրությունը։ Եթե բազան փոխվել է script.sql-ից հետո, արտահանել նոր Schema only script՝ բոլոր view/procedure/function/trigger-ներով։ .env, token, գաղտնաբառ կամ օգտատերերի անձնական տվյալներ ուղարկել պետք չէ։


## 0.3 լրացումներ

Նույնականացման քայլերը և server-side state bridge-ը՝ `AUTH_CONNECTION_HY.md`։ Իրական MSSQL փորձարկումները՝ `LOCAL_MSSQL_CHECKS_HY.md`։ Backup-ի ծագման միայն ընթերցման հարցումները՝ `BACKUP_PROVENANCE_READONLY.sql`։ Դրանք չեն հաստատում ինքնուրույն, որ script.sql-ը հենց վերջնական backup-ի նույն վիճակն է։

Երկրորդ բաժնի անգլերեն էջերը միացված են նույն API-ներին։ Տվյալների բովանդակության ավտոմատ թարգմանություն չկա։ Հանրային մեկնաբանությունները հաջորդ էջերով են բեռնվում։ Ուսանող–առարկա կապերի ցուցակն ու export-ը օգտագործում են նույն q/user_id/course_id ֆիլտրերը։
