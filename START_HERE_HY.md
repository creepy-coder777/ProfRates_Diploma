> Թարմացում՝ նոր գրանցումները թույլատրվում են միայն նախապես հաշվառված ուսանողներին։ Կիրառել database/04_student_roster.sql-ը և կարդալ docs/STUDENT_ROSTER_HY.md-ը։ Ստորև հին անուն/ամբիոն/խումբ ընտրելու քայլերը փոխարինվել են նոր ընթացքով։

# Նոր տարբերակի գործարկում

Օգտագործիր [FINAL_GUIDE_HY.md](FINAL_GUIDE_HY.md) ուղեցույցը։
Ստորև նախկին թիմային փուլի պատմական հրահանգներն են. դրանց AUTH_PROVIDER-ի պահանջն այլևս պարտադիր չէ։

---

# ProfRates — երկրորդ և երրորդ ուսանողների միասնական նախագիծ

Այս փաթեթը շարունակում է ձեր երկրորդ ուսանողի Backend-ը։ Ներառված են դրա frontend-ը,
երրորդ ուսանողի գնահատումները, like/dislike-ը, SQL հաշվարկները և նոր ստուգումները։
Առաջին ուսանողի իրական authentication-ը ներառված չէ․ դրա համար առկա ինտերֆեյսը պահպանված է։

## 1. Ինչ է փոխվել այս վերջնական տարբերակում

- Լրացված հարցաշարի միավորները անմիջապես մասնակցում են դասախոսի միջինին՝ անկախ մեկնաբանության կարգավիճակից։
- Մեկնաբանությունը կամընտիր է։ Առանց տեքստի գնահատման Status=Approved է, տեքստով՝ Pending։
- Status-ն այժմ մեկնաբանության մոդերացիայի կարգավիճակն է։ Rejected տեքստը չի հրապարակվում, բայց միավորները հաշվվում են։
- Խմբագրված տեքստը նորից Pending է, իսկ խմբագրված միավորները անմիջապես արտացոլվում են SQL view-ում։
- Նոր գնահատումների փոփոխման/ջնջման ժամկետը 24 ժամ է՝ RATING_EDIT_HOURS կարգավորումով։ Հին ժամկետները չեն վերագրվում։
- Like/dislike-ը պահվում է նոր dbo.RatingReactions կապի աղյուսակում։ Մեկ ուսանող՝ մեկ արձագանք նույն հրապարակված մեկնաբանության համար։
- PUT like/dislike-ը սահմանում է արձագանքը․ նույն PUT-ը կրկնելը հաշվիչը երկրորդ անգամ չի ավելացնում։ Frontend-ը նույն կոճակը կրկին սեղմելիս ուղարկում է DELETE reaction։
- Հին Likes/Dislikes թվերը պահպանվում են։ SQL trigger-ը դրանց ավելացնում/հանում է նոր արձագանքների փոփոխությունները։ Հին թվերի հեղինակները վերականգնել հնարավոր չէ։
- Top էջերը իրական տվյալներ են ստանում SQL-ի առկա uspLecturerRankings procedure-ից՝ BayesianScore-ով։ Սովորական AverageScore-ն առանձին ցուցանիշ է։

Կարևոր հետևանք․ թարմացումից հետո նախկին Pending/Rejected գնահատումների միավորներն էլ են հաշվվում։
Սա ընտրված կանոնի կիրառումն է բոլոր գնահատումների վրա։ Եթե նախկինում որևէ Rejected գրառման
միավորներն իսկապես անվավեր էին համարվել, անհրաժեշտ կլինի առանձին բիզնես կանոն՝ այդ գնահատումը բացառելու համար։

## 2. Ինչ ֆայլեր կան

| Ուղի | Նպատակ |
| --- | --- |
| app/student2 | Երկրորդ ուսանողի առկա CRUD, հարցաշար, որոնում, մոդերացիա |
| app/student3 | Ձեր գնահատումների, իրավունքի, անանունության, վիճակագրության և արձագանքների բաժինը |
| frontend | Ձեր HTML/CSS կայքը՝ անհրաժեշտ JavaScript միացումներով |
| database/ProfRates_databaza_original.bak | Ձեր ուղարկած սկզբնական backup-ը՝ անփոփոխ |
| database/01_original_export.sql | Ձեր ուղարկած սկզբնական SQL արտահանումը՝ անփոփոխ |
| database/02_upgrade_student3.sql | Գործող բազայի թարմացում․ նոր կապ և երկու view-ի փոփոխություն |
| docs/STUDENT3_TEST_REPORT.md | Այս տարբերակի փաստացի թեստերի արդյունք |
| docs/STUDENT3_FILE_AUDIT.json | Երկրորդ ուսանողի սկզբնական ZIP-ի համեմատությամբ փոփոխությունների ցանկ |
| docs/openapi.json | Բոլոր API-ների request/response փաստաթուղթ |
| requirements-student3-tested.txt | Փորձարկված միջավայրի գրադարանների տարբերակները |

Սկզբնական .bak-ը և սկզբնական արտահանումը **արդեն թարմացված բազա չեն**։ Դրանք օգտագործելուց հետո անհրաժեշտ է 02_upgrade_student3.sql-ը։

## 3. Բազան պատրաստել ձեր համակարգչում

Եթե ProfRates_databaza-ն արդեն կա և ձեր տվյալներով աշխատում է՝ **restore կամ սկզբնական export-ը նորից execute մի արեք**։

1. SSMS-ում միացեք ձեր սովորական Windows Authentication-ով։
2. Բացեք database/02_upgrade_student3.sql-ը։
3. Վերևի database ընտրացանկում ընտրեք ProfRates_databaza։
4. Execute արեք։

Այդ script-ը DROP/RESET չի կատարում, չի ջնջում հին գնահատումները և հաշվիչները։
Այն transaction-ում ստեղծում է RatingReactions-ը, դրա trigger-ը և թարմացնում ընդհանուր ու կիսամյակային summary view-երը։
Կրկնակի գործարկելիս նոր աղյուսակը երկրորդ անգամ չի ստեղծվում և հաշվիչները չեն վերականգնվում զրոյի։
SQL Server-ում իրական կատարման փորձը մեր միջավայրում հնարավոր չի եղել․ արդյունքը ստուգեք SSMS Messages-ում։

Եթե բազան ընդհանրապես չկա՝ SSMS-ի Restore Database գործիքով restore արեք ձեր սկզբնական .bak-ը,
անհրաժեշտության դեպքում Files բաժնում ընտրելով ձեր համակարգչի ճիշտ ուղիները, հետո կիրառեք 02 script-ը։
01_original_export.sql-ում կան սկզբնական համակարգչի ֆիզիկական ուղիները․ այն պատրաստի portable installer չէ։

## 4. Backend-ի կարգավորումը

Բացեք այս պանակը VS Code-ում։ Առաջին անգամ պատճենեք .env.example-ը .env անունով։
Եթե արդեն ունեք ձեր աշխատող .env-ը, պահեք այն և ավելացրեք միայն RATING_EDIT_HOURS=24-ը։

```dotenv
DB_SERVER=localhost\SQLEXPRESS
DB_NAME=ProfRates_databaza
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_TRUSTED_CONNECTION=true
DB_USER=
DB_PASSWORD=
AUTH_PROVIDER=
AUDIT_PROVIDER=
RATING_EDIT_HOURS=24
```

DB_SERVER-ը փոխարինեք SSMS-ում օգտագործվող իրական Server name-ով։ Driver-ը ընտրեք ձեր համակարգչում տեղադրված տարբերակով։
Encrypt/TrustServerCertificate արժեքները համապատասխանեցրեք ձեր SQL Server-ի certificate-ին։
Դատարկ AUTH_PROVIDER-ը մի շրջանցեք կեղծ UserID-ով։ Առաջին ուսանողը պետք է միացնի ստուգված նույնականացումը։

Կարող եք բացել START.cmd-ը․ այն տեղադրում է կախվածությունները, ստուգում է DB կապը և SQL upgrade-ի metadata-ն,
ապա գործարկում է սերվերը։ Պանակում .env-ի բացակայության դեպքում այն ստեղծում է օրինակն ու կանգնում՝ ձեր կարգավորումներին սպասելով։
Համակարգում պետք է տեղադրված լինեն Python-ը, SQL Server-ը և համապատասխան Microsoft ODBC Driver-ը։
Առաջին գրադարանների տեղադրման համար անհրաժեշտ է ինտերնետ։

Ձեռքով գործարկում՝

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -X utf8 -m tools.check_db
.venv\Scripts\python.exe -X utf8 -m tools.check_student3
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Կայք՝ http://127.0.0.1:8000/ ։ API փորձարկում՝ http://127.0.0.1:8000/docs ։
HTML-ը file://-ով մի բացեք․ օգտագործեք FastAPI-ի հասցեն։

## 5. Ինչ կարող եք անմիջապես ստուգել

RUN_TESTS.cmd-ը տեղադրում է development կախվածությունները և կատարում թեստերը։
Թեստերը փոխում են միայն հիշողության SQLite բազան․ ձեր SQL Server-ի տվյալներին չեն դիպչում։

```powershell
.venv\Scripts\python.exe -X utf8 -m pytest -q
.venv\Scripts\python.exe -X utf8 -m tools.export_schema
.venv\Scripts\python.exe -X utf8 -m tools.verify_schema
```

verify_schema-ն կարող է վերադարձնել warning/exit 2՝ ակտիվ trigger-ի առկայությունից․ դա trigger-ի իրական աշխատանքի ապացույց չէ։
check_student3-ն նույնպես metadata ստուգում է, ոչ թե transaction-ների իրական փորձարկում։

Մինչև authentication-ի միացումը ստուգեք՝

| API | Սպասվող արդյունք |
| --- | --- |
| GET /api/health/live | 200 |
| GET /api/health/ready | 200, եթե բազայի միացումը ճիշտ է |
| GET /api/lecturers | Իրական դասախոսներ և նոր SQL միջիններ |
| GET /api/questions | Ակտիվ հարցաշար՝ իրական QuestionID-ներով |
| GET /api/lecturers/{id}/statistics | Բոլոր գնահատումների միջինն ու պատասխանների բաշխումը |
| GET /api/lecturers/{id}/comments | Միայն հաստատված տեքստերը, Likes/Dislikes հաշվիչներով |
| GET /api/rankings | BayesianScore՝ SQL procedure-ից |
| GET /api/me/ratings | 401, եթե իրական authentication-ը դեռ միացված չէ |

Browser-ի F12 → Network → Fetch/XHR բաժնում ստուգեք հարցումների 200 պատասխաններն ու JSON տվյալների համապատասխանությունը էջին։

## 6. Ինչ ստուգել առաջին ուսանողի authentication-ը միացնելուց հետո

Առկա AUTH_PROVIDER-ը վերադարձնում է Principal։ Ուսանողը պետք է լինի ակտիվ, էլփոստը հաստատված։
Ինքնությունը երբեք չի վերցվում POST body-ի UserID-ից։ Հնարավոր է օգտագործել առկա
app.integrations.first_student:resolve_principal ինտերֆեյսը, երբ middleware-ը տրամադրում է վստահելի server-side state։
Cookie/session CSRF token-ի և session-ի իրական վավերացման համար պատասխանատու է առաջին ուսանողի մեխանիզմը։

| Գործողություն | API / ակնկալիք |
| --- | --- |
| Հասանելի առարկաներ | GET /api/me/rating-options |
| Ստեղծել գնահատում | POST /api/ratings → 201, միջինն անմիջապես փոխվում է |
| Առանց մեկնաբանության | Նույն POST, Comment=null կամ դատարկ → Approved, հանրային մեկնաբանություն չի ստեղծվում |
| Տեքստով գնահատում | Pending, տեքստը դեռ հանրային չէ |
| Հաստատում/մերժում | Երկրորդ ուսանողի PUT /api/admin/comments/{id}/moderation; միավորը չի փոխվում |
| Սեփականները | GET /api/me/ratings և GET /api/me/ratings/{id} |
| Փոփոխել | PUT /api/ratings/{id}, նույն կոնտեքստը և expected_updated_at-ը |
| Ջնջել | DELETE /api/ratings/{id}?expected_updated_at=...՝ ժամկետի մեջ |
| Արձագանքի վիճակ | GET /api/ratings/{id}/reaction → Likes, Dislikes, reaction: 1/-1/null |
| Like | PUT /api/ratings/{id}/like |
| Dislike | PUT /api/ratings/{id}/dislike |
| Չեղարկել | DELETE /api/ratings/{id}/reaction |

Մի քանի աղյուսակ փոխող գործողությունները մեկ transaction են։ Սխալի դեպքում rollback է։
Արձագանքների հաշվիչները Python-ը չի հաշվարկում․ SQL trigger-ն է պահում դրանք։
Հանրային պատասխաններում UserID, անուն, էլփոստ կամ խմբի տվյալներ չկան։ Լիազորված ադմինը ներքին view-ով կարող է տեսնել հեղինակին։

Ուսումնական իրավունքը ստուգվում է StudentCourses + Courses + ընթացիկ StudentAcademicProgress կապով։
StudentCourses-ում պատմական TermID չկա․ պատմական դասավանդման ամբողջական ապացույցը այս սխեմայով սահմանափակ է։
Կրկնության UNIQUE-ը շարունակում է լինել UserID+LecturerID+CourseID՝ առանց TermID-ի։

## 7. Ճարտարապետությունն ու պաշտպանության հիմնական բացատրությունը

app/main.py-ն միացնում է երկու ուսանողների router-ները և frontend-ը։
app/database.py-ն միակ production կապն է։ app/student2/dependencies.py-ն տրամադրում է SERIALIZABLE transaction։
app/student3/schemas.py-ն ստուգում է ID-ները, 1–5 միավորները, հարցերի կրկնությունը։
app/student3/service.py-ն ստուգում է կապերը և ownership-ը, պահում Ratings/RatingAnswers-ը, կարդում SQL summary-ը։
app/student3/reactions.py-ն ստուգում է հրապարակված տեքստը և կառավարում մեկ օգտատիրոջ արձագանքը։
SQL-ի PK-ն կանխում է կրկնակի արձագանքները, CHECK-ը թույլ է տալիս միայն -1/1, FK-ները պահպանում են ամբողջականությունը։
Արձագանքների գրառման ժամանակ SQL Server-ում օգտագործվում է նաև համապատասխան Ratings տողի update lock։
SQL հարցումների արժեքները parameterized են։ Runtime-ում create_all կամ migration ավտոմատ չի կատարվում։

Ինչո՞ւ բոլոր հարցերին նույն միավորը տալը չի մերժվում․ դա ինքնին ապացույց չէ պատահական գնահատման։
Ինչո՞ւ տեքստի մերժումը չի հանում միավորը․ տեքստի ընդունելիությունն ու հարցաշարի միավորները տարբեր տվյալներ են։
Ինչո՞ւ առանձին արձագանքի աղյուսակ․ հաշվիչը չի ասում՝ ով է արձագանքել։
Ինչո՞ւ SQL view/procedure․ բոլոր էջերը ստանում են նույն հաշվարկը, Python-ում նույն բանաձևը չի կրկնվում։
Ինչո՞ւ 57 թեստը դեռ MSSQL աշխատանքի ապացույց չէ․ SQLite-ը չի ստուգում իրական SQL Server trigger-ի, locking-ի և driver-ի վարքը։

Նախորդ docs-ի սկզբնական ուղեցույցների հակասող հատվածները վերաբերում են նախորդ տարբերակին։
Այս START_HERE_HY.md-ն և թարմացված STUDENT3_TEST_REPORT.md-ն այս փաթեթի վերջնական կանոնների աղբյուրն են։
