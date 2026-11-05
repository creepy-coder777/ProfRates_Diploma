# Երրորդ ուսանողի բաժին․ իրականացում և պաշտպանության ուղեցույց

Այս տարբերակը շարունակությունն է կցված `ProfRates_Student2_Backend(1).zip` նախագծի։
Առանձին authentication, երկրորդ DB connection, migration կամ նոր բազա չի ստեղծվել։
Բոլոր փոփոխված և նոր ֆայլերի ամբողջական կոդը ներառված է նախագծում։

## 1. Ուսումնասիրության արդյունք

Հիմնական կառուցվածքը՝

| Ուղի | Իրական նշանակություն |
| --- | --- |
| `app/main.py` | FastAPI-ի `app`, router-ների գրանցում, health API, frontend-ի մատուցում |
| `app/config.py` | Pydantic Settings, `.env`-ի ընթերցում, գաղտնաբառի `SecretStr` |
| `app/database.py` | SQLAlchemy engine, `mssql+pyodbc`, Windows/SQL authentication, ODBC escaping |
| `app/security.py` | `Principal` և արտաքին `AUTH_PROVIDER` adapter, ադմինի ստուգում |
| `app/integrations/first_student.py` | Վստահելի server-side state-ից Principal ստանալու ինտերֆեյս |
| `app/student2/tables.py` | SQLAlchemy Core mapping՝ JSON դաշտերից և view-երի սահմանումներից |
| `app/student2/schemas.py` | Pydantic մուտքային սխեմաներ՝ CRUD, հարցաշար, moderation |
| `app/student2/service.py` | Բիզնես կանոններ, հարցումներ, audit, moderation, pagination |
| `app/student2/router.py` | Հանրային և ադմինի API endpoint-ներ |
| `app/student2/dependencies.py` | SERIALIZABLE transaction, commit/rollback, SQL սխալների անվտանգ պատասխաններ |
| `docs/verified_schema.json` | Նախորդ SQL script-ից ստացված դաշտերի նկարագրություն |
| `docs/schema_contract.json` | PK/FK/UNIQUE-երի և երեք view-երի փաստագրված պայմանագիր |
| `tools/` | Միացման, metadata export-ի, schema-ի, auth-ի և rollback smoke ստուգումներ |
| `tests/` | FastAPI TestClient և SQLite թեստային fixture-ներ |
| `frontend/` | Ներառված կայքը՝ երկրորդ ուսանողի արդեն կատարված API կապերով |

Ամբողջ սկզբնական ֆայլերի ցանկն ու SHA-256 համեմատությունը տրված են
`STUDENT3_FILE_AUDIT.json`-ում։ Նկարների բովանդակությունը կոդ չէ․ դրանք պահպանվել են։
ZIP-ում չկան `pyproject.toml` և ամբողջական schema-only SQL script։

SQL հարցումները կատարվում են SQLAlchemy Core-ով՝ `select`, `insert`, `update`, `delete`։
Արժեքները փոխանցվում են bind parameter-ներով, ոչ թե SQL տողի մեջ միացնելով։
SQLAlchemy-ն SQL Server-ի համար ընտրում է համապատասխան SQL շարահյուսությունը։
`get_db`-ի մեկ transaction-ը ներառում է հիմնական գրառումը, պատասխաններն ու audit-ը։
Սխալի դեպքում կատարվում է rollback։ IntegrityError → 409, DataError → 422,
միացման/SQL խնդիր → 503՝ առանց connection string-ի կամ SQL գաղտնիքների վերադարձի։

Երկրորդ ուսանողի առկա API-ների խմբերը՝

| Մեթոդ և URL | Նպատակ |
| --- | --- |
| `GET /api/lecturers`, `GET /api/lecturers/{id}` | Որոնում, ֆիլտրում, դասախոսի տվյալներ, view-ից վարկանիշ |
| `GET /api/questions` | Ակտիվ հարցերի միասնական աղբյուր |
| `GET /api/academic/{resource}` | Ակտիվ ուսումնական տեղեկատուներ |
| `GET /api/lecturers/{id}/comments` | Հաստատված հանրային մեկնաբանություններ |
| `GET/POST /api/admin/lecturers` | Դասախոսների ցանկ/ստեղծում |
| `PUT/DELETE /api/admin/lecturers/{id}` | Փոփոխում/ապաակտիվացում |
| `GET/POST /api/admin/questions` | Հարցաշարի ցանկ/ավելացում |
| `PUT /api/admin/questions/order` | Հերթականության փոփոխում |
| `PUT/DELETE /api/admin/questions/{id}` | Փոփոխում/ապաակտիվացում |
| `GET /api/admin/academic/catalog` | Թույլատրելի ուսումնական ռեսուրսների սխեմաներ |
| `GET/POST /api/admin/academic/{resource}` | Ինստիտուտ, ֆակուլտետ, ամբիոն, մասնագիտություն, խումբ, առարկա |
| `PUT/DELETE /api/admin/academic/{resource}/{id}` | Փոփոխում/ապաակտիվացում |
| `GET /api/admin/semesters`, `GET /api/admin/student-options` | Ընտրացանկեր |
| `GET/POST /api/admin/student-courses` | Ուսանող–առարկա կապերի որոնում/ավելացում |
| `DELETE /api/admin/student-courses/{id}` | Կապի հեռացում |
| `PUT /api/admin/courses/{id}/lecturer` | Դասախոսի նշանակում |
| `GET /api/admin/comments` | Մեկնաբանությունների ֆիլտրված հերթ |
| `PUT /api/admin/comments/{id}/moderation` | Հաստատում/մերժում՝ expected_status ստուգումով |

Կան նաև համապատասխան `.../export` CSV API-ներ։ Ճշգրիտ ամբողջական ցանկը՝
թարմացված `docs/openapi.json`-ում և գործարկված կայքի `/docs` էջում։

## 2. Բազայի իրական հասանելիությունն ու սահմանափակումները

Փաստաթղթային սխեման և կցված նոր `.bak`-ը նույնը լինելը **հաստատված չէ**։
`localhost` և `localhost\SQLEXPRESS` հասցեներին Windows Authentication-ով
կատարված միացման փորձերը ձախողվել են։ Բազա չի restore արվել և տվյալներ չեն փոխվել։
`.bak`-ը SQL Server-ի binary backup է․ այն սովորական SQL տեքստ չէ։
Առանց հասանելի SQL Server-ի հնարավոր չէր ստանալ դրա ամբողջական կառուցվածքը։

Փաստագրված կապերը՝

| Աղյուսակ | Կարևոր դաշտեր և սահմանափակումներ |
| --- | --- |
| `Ratings` | RatingID PK, UserID FK, LecturerID FK, CourseID FK, TermID FK, Comment, Status, ApprovedByAdminID, Likes, Dislikes, CreatedAt, UpdatedAt, EditExpiry |
| `Ratings` UNIQUE | UserID + LecturerID + CourseID. TermID-ը UNIQUE-ի մաս չէ |
| `RatingAnswers` | AnswerID PK, RatingID FK, QuestionID FK, Score; UNIQUE RatingID + QuestionID |
| `Questions` | QuestionID, Text, Category, SortOrder, IsActive |
| `StudentCourses` | UserID + CourseID UNIQUE, EnrolledAt․ TermID չունի |
| `Courses` | LecturerID, SpecializationID, CurriculumSemesterNumber, IsActive |
| `StudentAcademicProgress` | UserID + TermID PK, SemesterNumber, IsCurrent; մեկ ընթացիկ գրառում՝ filtered UNIQUE UserID |
| `Users` | UserID, Status, IsEmailVerified և անձնական դաշտեր |

Մեկնաբանությունը `Ratings.Comment` դաշտում է, իսկ միավորները՝ առանձին
`RatingAnswers`-ում։ Status-ը պատկանում է ամբողջ գնահատմանը, ոչ թե միայն տեքստին։

Հասանելի երեք view-ի սահմանումները պահպանված են `schema_contract.json`-ում։
Դրանց հիմքով `vwLecturerRatingSummary`-ը SQL-ում միջինացնում է Approved
գնահատումների `OverallScore`-ները և հաշվում գնահատումների/պատասխանների քանակը։
`OverallScore`-ի աղբյուրը `vwRatingScores`-ն է, որի ամբողջական սահմանումը
այս պայմանագրում չկա․ կշիռների կամ գործակիցների վերաբերյալ ենթադրություն չի արվել։
`vw_Ratings_Public`-ը ֆիլտրում է Approved-ը, իսկ admin view-ը ներառում է անձնական տվյալներ։
Trigger-ների, procedure-ների և EditExpiry default-ի ամբողջական նկարագրությունը բացակայում է։

### Անհրաժեշտ արտահանումը

Առկա նախագծի պանակում գործարկիր՝

```powershell
.venv\Scripts\python.exe -m tools.check_db
.venv\Scripts\python.exe -m tools.export_schema
.venv\Scripts\python.exe -m tools.verify_schema
```

Ուղարկիր `exports/schema_metadata.json` և `exports/schema_verification.json`։
Export գործիքն արդեն ստանում է tables, columns, defaults, computed columns,
PK/UNIQUE indexes, FK, CHECK, SQL modules, triggers, parameters։ Անհրաժեշտ է
`VIEW DEFINITION` իրավունքը․ այն տրամադրում է բազայի պատասխանատուն։

Այլընտրանք՝ SSMS → բազայի աջ կոճակ → Tasks → Generate Scripts →
`Script entire database and all database objects` → Advanced →
`Types of data to script = Schema only`։ Միացրու `Script Triggers`,
`Script Indexes`, `Script Primary Keys`, `Script Foreign Keys`,
`Script Unique Keys`, `Script Check Constraints`, `Script Defaults`։
Ներառիր view-երը, stored procedure-ները և functions-ը։ Պահպանիր Unicode SQL ֆայլ։
Սա արտահանում է․ ստացված script-ը աշխատեցնել պետք չէ։ Գաղտնաբառերը կամ `.env`-ը մի ուղարկիր։

## 3. Նոր բաժնի կառուցվածքը

| Ֆայլ | Ինչ է անում և ինչու է պետք |
| --- | --- |
| `app/student3/schemas.py` | Request-ի ID-ների, 1–5 միավորների, կրկնվող հարցերի ստուգում։ UserID/Status/Likes ուղարկելն արգելված է |
| `app/student3/dependencies.py` | Առկա authentication-ից Principal, ակտիվ/հաստատված Users գրառման ստուգում, այլ origin-ից գրանցման արգելք |
| `app/student3/service.py` | Ուսումնական իրավունքի, ownership-ի, հարցաշարի ստուգում, CRUD, SQL view-ից վիճակագրություն |
| `app/student3/router.py` | Նոր endpoint-ներ․ վերօգտագործում է get_db, pagination, get_actor, public view |
| `frontend/js_codes/student3_rate.js` | Առարկայի ընտրություն, POST/PUT, սեփական հին գնահատման բեռնում |
| `frontend/js_codes/student3_mine.js` | Իրական սեփական գնահատումներ, էջավորում, փոփոխման հղում, DELETE |
| `tests/test_student3.py` | Իրավունքների, սխալ հարցաշարի, անանունության, moderation-ի, rollback-ի թեստեր |

Փոփոխված են նաև `app/main.py`-ն՝ նոր router-ը գրանցելու համար,
`app/student2/service.py`-ի audit-ը՝ ուսանողի UserID-ն ներքին մատյանում պահելու համար,
և moderation-ը՝ դատարկ Comment-ով գնահատումն էլ հաստատելու հնարավորություն տալու համար։
Մոդերացիայի endpoint-ը, status-ները և expected_status ստուգումը նույնն են։
Առկա մեկնաբանությունների հերթը շարունակում է ցույց տալ միայն տեքստ ունեցողները․
բոլոր գնահատումների համար ավելացվել է ադմինի `/api/admin/rating-queue` API-ն։
Դրա համար նոր admin դիզայն չի ստեղծվել․ հասանելի է `/docs`-ից։

## 4. Նույնականացում և ուսումնական իրավունք

Սեփական բաժնի գործողություններին անհրաժեշտ է `Principal(user_id=<Users.UserID>, is_admin=False)`։
Այն վերցվում է բացառապես `get_current_user`-ից։ Request-ի body-ի կամ header-ի
StudentID/UserID/role-ը չի կարող փոխարինել նույնականացմանը։
Դատարկ `AUTH_PROVIDER`-ի դեպքում պատասխանն է 401։ Իրական login/session/JWT
ինտեգրումը **սպասում է առաջին ուսանողին**։ Թեստերի dependency override-ը միայն
թեստում է և production adapter չէ։

Առաջին ուսանողը ստուգում է session/JWT-ի վավերությունը, ժամկետը, ստորագրությունը,
ելքից հետո անվավերացումը, cookie-ի դեպքում՝ CSRF պաշտպանությունը։ Այնուհետև
middleware-ը կարող է դնել `request.state.verified_profrates_principal` և միացնել՝

```dotenv
AUTH_PROVIDER=app.integrations.first_student:resolve_principal
```

Այս տողը միայն adapter-ն է միացնում․ middleware-ի բացակայությամբ միևնույն է 401 է։
Frontend-ը վերօգտագործում է առկա `ProfRatesAuth.getHeaders()`-ը և same-origin cookie-ները։

Գնահատման իրավունքի հարցումը միացնում է՝
StudentCourses → Courses → Lecturers, և StudentAcademicProgress → AcademicTerms։
Պետք է լինեն նույն UserID-ի ուսանող–առարկա կապ, առարկայի ճիշտ LecturerID,
ակտիվ առարկա/դասախոս, ընթացիկ progress, համապատասխան TermID և ուսումնական semester։
**Սահմանափակում.** StudentCourses-ում enrollment-ի TermID չկա, իսկ Courses-ի դասախոսը
փոփոխելի է։ Այս կառուցվածքով հնարավոր չէ ապացուցել պատմական կոնկրետ կիսամյակի
դասավանդումը։ Ապահովվում է առկա ուսումնական կապը․ պատմական իրավունքի քաղաքականությունը
պետք է հաստատել թիմի հետ։ Սխեմայի նոր կապ չի հորինվել։

## 5. API-ները և օրինակները

Բոլոր ID-ները ստորև օրինակ են․ իրականները վերցրու API-ի պատասխաններից։

| Մեթոդ և URL | Իրավունք | Պատասխան / սխալներ |
| --- | --- | --- |
| `GET /api/me/rating-options` | Ակտիվ, հաստատված ուսանող | items՝ CourseID, LecturerID, Name, TermID; 401/403/503 |
| `POST /api/ratings` | Նույն ուսանող, ուսումնական կապ | 201 PrivateRating; 403 կապ չկա, 409 կրկնություն/հարցաշար, 422 սխալ body |
| `GET /api/me/ratings` | Նույն ուսանող | items,total,page,page_size; միայն սեփականները |
| `GET /api/me/ratings/{id}` | Հեղինակ | PrivateRating; ուրիշի և բացակայողի համար նույն 404 |
| `GET /api/me/ratings/{id}/questions` | Հեղինակ | Նախկին հարցերի Text/Category/ID-ները, նույնիսկ ապաակտիվացվածները |
| `PUT /api/ratings/{id}` | Հեղինակ, ուսումնական կապ, ժամկետ | 200 PrivateRating; 404 ոչ սեփական, 409 ժամկետ/տարբերակ/կոնտեքստ |
| `DELETE /api/ratings/{id}?expected_updated_at=...` | Նույն պայմանները | 200 `{"deleted":1}`; նախ պատասխանների, ապա գնահատման DELETE |
| `GET /api/lecturers/{id}/ratings` | Հանրային | Approved գնահատումներ՝ allowlist դաշտերով, էջավորում |
| `GET /api/lecturers/{id}/statistics` | Հանրային | SQL summary և Approved պատասխանների 1–5 բաշխում |
| `GET /api/admin/rating-queue` | Վավեր ադմին | Բոլոր գնահատումների հերթ՝ առկա admin view-ից |
| `GET /api/admin/lecturers/{id}/rating-statistics` | Վավեր ադմին | Նույն summary + մեկնաբանությունների status-ների քանակներ |
| `GET/PUT/DELETE /api/ratings/{id}/like` | Ուսանող | 501․ իրական հավանումների persistence-ը դեռ հաստատված չէ |

POST body՝

```json
{
  "LecturerID": 1,
  "CourseID": 3,
  "TermID": 2,
  "Comment": "Հասկանալի բացատրություններ",
  "answers": [
    {"QuestionID": 7, "Score": 5},
    {"QuestionID": 9, "Score": 4}
  ]
}
```

`answers`-ը պետք է պարունակի **բոլոր իրական ակտիվ հարցերը**, ոչ թե հենց այս երկու օրինակը։
Python-ը ստուգում է ինքնությունը, կապը, հարցերի ID-ների ամբողջականությունը և կրկնությունը։
SQL Server-ին ուղարկվում են parameterized SELECT-ներ, մեկ Ratings INSERT,
RatingAnswers INSERT-ներ և ActivityLogs INSERT։ Դրանք մեկ transaction են։
Գնահատումը միշտ սկսում է Pending-ից, իսկ AdminID-ը հաճախորդը չի սահմանում։

201 պատասխանի ձևը՝

```json
{
  "RatingID": 15,
  "LecturerID": 1,
  "CourseID": 3,
  "TermID": 2,
  "Comment": "Հասկանալի բացատրություններ",
  "Status": "Pending",
  "CreatedAt": "2026-10-22T16:00:00",
  "UpdatedAt": "2026-10-22T16:00:00",
  "EditExpiry": null,
  "answers": [{"QuestionID": 7, "Score": 5}, {"QuestionID": 9, "Score": 4}]
}
```

PUT-ը վերցնում է նույն body-ն և ավելացնում է GET-ից ստացած `expected_updated_at`-ը։
LecturerID/CourseID/TermID փոխել չի կարելի։ Հին գնահատման համար պահանջվում են հենց
նախկին պատասխանների հարցերի ID-ները, որպեսզի ապաակտիվացված հարցերը չկորչեն։
Comment/պատասխանները փոխելուց հետո Status-ը դառնում է Pending, ApprovedByAdminID-ը՝ NULL։
Վարկանիշը view-ում ինքնաբերաբար արտացոլում է հաստատման կորուստը։

Փոփոխում և ջնջում թույլատրվում են միայն DB-ում առկա ապագա EditExpiry-ի դեպքում։
NULL-ը անվտանգորեն արգելվում է․ ժամկետի default/trigger-ը դեռ պետք է ստուգվի։
Եթե նոր INSERT-ից հետո EditExpiry-ը NULL է, ստեղծումն աշխատում է, իսկ խմբագրումն ու
ջնջումը 409 են տալիս։ Դա թաքցված չէ․ մինչև քաղաքականության հաստատումը նոր ժամկետ չի նշանակվում։

DELETE-ի query-ի `expected_updated_at`-ը URL-encode արա։ SQL-ը նախ ownership-ը,
վերջնաժամկետը և թարմացման տարբերակն է ստուգում, ապա մեկ transaction-ում հեռացնում է
պատասխանները և գնահատումը։ Եթե իրական բազայում կան այլ FK կախվածություններ,
constraint-ը կարող է 409 վերադարձնել և ամբողջ գործողությունը rollback անել։

Հաստատում՝ առկա երկրորդ ուսանողի API-ով․

```http
PUT /api/admin/comments/15/moderation
Content-Type: application/json

{"status":"Approved","expected_status":"Pending"}
```

Պատասխան՝ `{"RatingID":15,"Status":"Approved","rating_source":"dbo.vwLecturerRatingSummary"}`։
Rejected-ի համար նույն body-ում status-ը փոխիր։ Դատարկ Comment ունեցող գնահատումն էլ
այժմ հնարավոր է հաստատել․ այդ դեպքը հասանելի է rating-queue-ում։

## 6. Անանունություն և հավանումներ

Հանրային նոր գնահատման պատասխանում կան միայն RatingID, LecturerID, OverallScore,
Comment, CreatedAt։ SQL-ը չի միացնում Users-ը․ անձնական տվյալները նախ չի բեռնում,
ապա միայն JSON-ից հեռացնում։ PublicRating սխեման երկրորդ սահմանափակումն է։
Սեփական endpoint-ներում էլ UserID, Email, ApprovedByAdminID չեն վերադարձվում։
Ուրիշի ID-ի հարցման և գոյություն չունեցող ID-ի սխալը նույն 404-ն է։
Հեղինակի UserID պարունակող հանրային URL գոյություն չունի։

Անանունությունը վերաբերում է համակարգի անձնական նույնականացուցիչներին։ Տեքստում
ուսանողի կողմից իր անունը գրելը, ժամանակային համադրությունը կամ փոքր խմբերի մասին
արտաքին տեղեկությունը ավտոմատ կերպով չեն վերացվում։ Հանրային ամսաթիվն ու միավորը
պահպանված են առկա կայքի վարքին համապատասխան։ DB ադմինը և լիազորված moderation
ադմինը կարող են ներքին կապով բացահայտել հեղինակին․ ադմինի API-ն հանրային չէ։

Likes/Dislikes թվային հաշվիչները չեն ասում՝ **ով** է հավանել։ Օգտատեր–մեկնաբանություն
աղյուսակ կամ համապատասխան procedure այս ZIP-ի սխեմայում չկա։ Հետևաբար այս տարբերակը
չի ավելացնում կեղծ localStorage հավանում կամ կրկնության ստուգում միայն Python հիշողությամբ։
Like-ի երեք գործողությունները հստակ 501 են վերադարձնում և ոչինչ չեն փոխում։
Իրական export-ից հետո պետք է վերօգտագործել առկա UNIQUE/trigger/procedure-ը։ Եթե այն
բացակայի, անհրաժեշտ նոր կապի առաջարկը պետք է առանձին համաձայնեցնել․ այստեղ DDL չկա։

## 7. Վարկանիշ և վիճակագրություն

Python-ում նոր կշիռ, գործակից, ընդհանուր միջին կամ trigger-ի փոխարինում չկա։
AverageScore/TotalRatings/TotalAnswers-ը կարդացվում են SQL view-ից։ INSERT/UPDATE/DELETE-ից
հետո view-ը տվյալները կարդում է նոր վիճակով․ առանձին Python recalculation չի պահանջվում։
Դրա իրական MSSQL վարքը դեռ պահանջում է տեղային ստուգում։

Բաշխումը առանձին SQL `GROUP BY RatingAnswers.Score` հարցում է՝ Approved գրառումներով։
Այն **հարցերի պատասխանների բաշխումն է**, ոչ թե կլորացված OverallScore-ների բաշխում։
Օրինակ՝ մեկ գնահատում՝ 6 հարցով, կարող է տալ 6 պատասխան բաշխման մեջ, բայց TotalRatings=1։
Պատասխանը դա նշում է `distribution_unit=approved_question_answers` դաշտով։
Pending/Rejected մեկնաբանությունների քանակները հասանելի են միայն ադմինին։
Ժամանակային միտումների նոր dashboard չի ստեղծվել։

## 8. Frontend-ի կապը

Աշխատանքի հիմքը backend ZIP-ի արդեն միացված frontend-ն է։ Առանձին կցված
`ProfRates(2).zip`-ը համեմատության աղբյուր է․ այն չի վերագրում երկրորդ ուսանողի API կապերը։
`ProfRates_web.zip` անունով առանձին ֆայլ չի տրամադրվել։

Նախկին 12/10 ստատիկ հարցերը արդեն հեռացված են backend ZIP-ի rate էջից։
`student2_rate.js`-ը հարցերը ստանում է `/api/questions`-ից։ Նոր բաժինը միացնում է
նախկինում բացակայող `ProfRatesRatings.submit`-ը։ Հարցերի թիվը կոդում ամրագրված չէ։
Պատասխաններն ուղարկվում են իրական QuestionID-ներով, ոչ թե ցուցադրման հերթականությամբ։
Թարմ հարցաշարի անհամապատասխանության դեպքում backend-ը տալիս է 409։

`rate_arm.html`/`rate_eng.html`-ում ավելացվել է student3_rate script-ը՝ առկա script-ից առաջ։
Առարկաները գալիս են `/api/me/rating-options`-ից։ URL-ի ID-ները պարզապես ընտրություն են․
backend-ը դրանք կրկին ստուգում է։ `?rating_id=15`-ը բեռնում է սեփական հին գնահատումը։
`ratings_arm.html`/`ratings_eng.html`-ի ցուցադրական քարտերն ու միայն DOM փոխող script-ը
փոխարինվել են իրական բեռնումով։ Օգտագործվում են նույն CSS դասերը, CSS-ը չի փոխվել։
Սեփական գնահատման քարտը ցույց է տալիս դասախոսի անունը, մեկնաբանությունը, ամսաթիվն ու
moderation status-ը․ հին կեղծ միջին միավորները չեն ցուցադրվում։
Այս frontend փոփոխությունները դեռ պետք է փորձարկել իրական browser/login/MSSQL շղթայով։
Profile-ի առկա վարկանիշն ու մեկնաբանությունների կապը պահպանվել են։ Like կոճակ չի
ակտիվացվել առանց հաստատված persistence-ի։

## 9. Գործարկում և փորձարկում

ZIP-ը բացելուց հետո terminal-ը բացիր այն պանակում, որտեղ `app` և `requirements.txt` կան։

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

`.env`-ում գրիր քո SSMS-ի իրական Server name-ը, DB_NAME=ProfRates_databaza,
DB_TRUSTED_CONNECTION=true, DB_USER և DB_PASSWORD դատարկ։ Driver-ը վերցրու տեղադրվածներից՝

```powershell
.venv\Scripts\python.exe -c "import pyodbc; print(pyodbc.drivers())"
```

Եթե տեղադրված է միայն 17-ը, գրիր `DB_DRIVER=ODBC Driver 17 for SQL Server`։
Եթե 18-ն է՝ գրիր 18։ Այս միջավայրում հաստատվել է ODBC Driver 17-ի առկայությունը, և .env.example-ում նշված է 17-ը։ Այլ համակարգչում կրկին ստուգիր տեղադրված տարբերակը։
Encrypt/TrustServerCertificate-ը համապատասխանեցրու տեղային SQL Server-ի certificate-ին։
`AUTH_PROVIDER`-ը թող դատարկ, մինչև իրական adapter-ը պատրաստ լինի․ պահպանվող API-ների 401-ը սպասված է։
AUDIT_PROVIDER-ը կարող է մնալ դատարկ․ օգտագործվում է ActivityLogs-ը։
`.env`, `.venv/`, `exports/` արդեն Git-ից բացառված են։

```powershell
.venv\Scripts\python.exe -m tools.check_db
.venv\Scripts\python.exe -m tools.export_schema
.venv\Scripts\python.exe -m tools.verify_schema
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

`check_db`՝ SELECT 1, միացման ստուգում։ `verify_schema`՝ փաստաթղթային պայմանագրի
համեմատություն իրական metadata-ի հետ․ trigger-ի իրական աշխատանքի ապացույց չէ։
`pytest`՝ տեղային մեկուսացված SQLite թեստեր․ production fallback չկա։
`tools.smoke_mssql`-ը երկրորդ ուսանողի rollback գործիքն է, ոչ թե նոր բաժնի ամբողջական թեստ։
Նոր բաժնի թեստերը՝ `python -m pytest tests/test_student3.py -q`։

Բացիր `http://127.0.0.1:8000/docs`, կայքը՝ `http://127.0.0.1:8000/`։
Frontend-ը բացիր նույն host/port-ից, ոչ թե file://-ով։
Իրական authentication-ից հետո `/docs`-ից կամ կայքից ստուգիր հերթով՝
rating-options → questions → POST → սեփական GET → admin approve → public statistics →
սեփական PUT → public-ից անհետացում մինչև վերահաստատում → DELETE։
Մասնավոր գործողությունների համար կիրառիր իրական auth header/cookie-ն և CSRF token-ը,
եթե առաջին ուսանողի մեխանիզմը դա պահանջում է։ Կեղծ token-ի օրինակ չի տրամադրվում։

Թեստերը փոխում են միայն հիշողության SQLite fixture-ը և հետո ոչնչացնում այն։
Իրական բազայում գնահատումներ չեն ստեղծվել կամ ջնջվել։ Իրական SQL Server-ում mutation
թեստեր անելուց առաջ արտահանիր ու ստուգիր trigger-ները, defaults-ը, FK-ները և procedure-ները,
ապա օգտագործիր հատուկ թեստային հաշիվ/տվյալներ։ Unknown trigger-ի արտաքին ազդեցությունը
միայն rollback-ով միշտ վերականգնել հնարավոր չէ։

Թեստերի այս գործարկման փաստացի արդյունքը՝ `STUDENT3_TEST_REPORT.md`-ում։

## 10. Պաշտպանության հնարավոր հարցերը

1. Ինչո՞ւ FastAPI dependency։ Այն մեկ տեղից տրամադրում է ստուգված ինքնությունը և նույն transaction-ը։
2. Ինչո՞ւ UserID չես ընդունում body-ում։ Հաճախորդը կարող էր ուրիշի անունից գնահատում ուղարկել։
3. Ինչպե՞ս է ապացուցվում ուսումնական կապը։ StudentCourses, Courses, current progress միացմամբ․ պատմական կապի սահմանափակումը նշված է։
4. Ինչո՞ւ առանձին Ratings/RatingAnswers։ Գնահատումը մեկ գործողություն է, հարցերի պատասխանները՝ դրա բազմաթիվ կախյալ գրառումները։
5. Ինչո՞ւ transaction։ Որպեսզի գնահատումն առանց պատասխանների կամ audit-ի չմնա։
6. Ինչպե՞ս է կանխվում կրկնությունը։ Service-ի ստուգում + փաստագրված SQL UNIQUE + SERIALIZABLE transaction․ իրական MSSQL concurrency-ն դեռ թեստի կարիք ունի։
7. Ինչո՞ւ հարցերի թիվը ֆիքսված չէ։ Հարցաշարը երկրորդ ուսանողի կառավարվող տվյալ է։
8. Ինչո՞ւ հին հարցերը պահել։ Հակառակ դեպքում հին պատասխանի իմաստը կկորչեր հարցի փոփոխումից հետո։
9. Ինչո՞ւ Status-ը նորից Pending է։ Խմբագրված չհաստատված բովանդակությունը չպետք է հանրայնացվի հին հաստատումով։
10. Ինչո՞ւ վարկանիշը Python-ում չես հաշվարկում։ SQL view-ն է ընդհանուր միակ աղբյուրը՝ նույնը բոլոր էջերի համար։
11. Ինչո՞ւ Like-ը 501 է։ Հաշվիչը չի պահում հեղինակային կապը․ առանց persistence-ի կրկնության կանխումը կեղծ կլիներ։
12. Ինչո՞ւ NULL EditExpiry-ն արգելվում է։ Ժամկետի անհայտ կանոնի փոխարեն անվտանգ սահմանափակում է․ ժամերի նոր թիվ չի հորինվել։
13. Ինչո՞ւ SQLite թեստը բավարար չէ։ SQL Server-ի locking, trigger, CHECK, datetime և driver վարքերը տարբեր են։
14. Ադմինից էլ անանո՞ւն է։ Ոչ․ հանրային անանունությունը չի վերացնում ներքին պատասխանատվության կապը։

## Վերջնական սահմանները

**Իրականացված է**՝ փաստագրված սխեմայի վրա CRUD, ստուգումներ, հանրային allowlist,
SQL summary, պատասխանների բաշխում, frontend կապի կոդ և թեստեր։
**Սպասում է առաջին ուսանողի ինտեգրմանը**՝ իրական authentication/session/CSRF ամբողջ շղթան։
**Սպասում է իրական SQL արտահանմանը**՝ backup-ի համապատասխանություն, trigger/default/procedure
ուսումնասիրություն, EditExpiry կանոն, իրական likes persistence, պատմական ուսումնական կապի հաստատում։
**Փորձարկումը դեռ կատարված չէ**՝ իրական MSSQL CRUD/concurrency և իրական browser/auth շղթան։
Այս տարբերակը չի ներկայացվում որպես ամբողջությամբ ավարտված production համակարգ։


## Այս շարունակության լրացուցիչ ուղղումները

`tests/test_student2.py`-ում տեքստային ֆայլերի ընթերցումն այժմ հստակ UTF-8 է՝ Windows-ի cp1252 սխալից խուսափելու համար։ `app/student3/service.py`-ում UpdatedAt-ի տարբերակը համեմատվում է արդեն կարդացված datetime-ի հետ, իսկ ժամկետը ստուգվում է SQL-ի ժամով․ սա վերացնում է SQLite-ի timestamp տեքստային ներկայացման տարբերությունից առաջացող սխալ 409-ը։ Իրական SQL Server locking-ի թեստ դեռ չի կատարվել։

Ստուգված միջավայրի կախվածությունների ճշգրիտ ցուցակը՝ `requirements-student3-tested.txt`։ Նախկին requirements ֆայլերը պահպանված են։
