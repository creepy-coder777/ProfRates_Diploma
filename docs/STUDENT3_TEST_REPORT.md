# Վերջնական տարբերակի ստուգումներ — 2026-10-22

- Ամբողջ նախագծի վերջին գրանցված արդյունք՝ 57 passed, 1 warning։
- SQLite հիշողության մեկուսացված բազայով ստուգված են երկրորդ և երրորդ ուսանողների API-ները, իրավունքը, հարցաշարը, սեփականությունը, ժամկետը, անմիջական միավորների հաշվառումը, տեքստի մոդերացիան, like/dislike-ի կրկնումը/փոխարինումը/չեղարկումը, հին հաշվիչների պահպանումը և rollback-ը։
- Rankings wrapper-ը ստուգված է procedure-ի կանչի և inactive դասախոսների ֆիլտրման մասով։ SQL procedure-ի իրական MSSQL կատարումը չի փորձարկվել։
- SQLite fixture-ն օգտագործում է SQL trigger-ների թեստային համարժեքներ։ SQL Server-ի նոր trigger-ը այս միջավայրում չի գործարկվել։
- Փոփոխված JavaScript ֆայլերի շարահյուսությունը ստուգված է։ Browser-ի իրական login/API/MSSQL շղթան չի փորձարկվել։
- SQL migration-ը պատրաստված է մեկ transaction-ով, բայց իրական SQL Server-ում չի գործարկվել։ Սկզբնական .bak-ը չի restore արվել։
- Միակ նախազգուշացումը Starlette TestClient/httpx deprecation-ն է։

## Ձեր համակարգչում

1. SSMS-ում գործող բազայի վրա կիրառեք database/02_upgrade_student3.sql-ը։
2. Կարգավորեք .env-ը։
3. Գործարկեք tools.check_db, tools.check_student3, tools.export_schema, tools.verify_schema։
4. Գործարկեք RUN_TESTS.cmd-ը և START.cmd-ը։
5. Իրական authentication-ի միացումից հետո կատարեք frontend-ի մասնավոր գործողությունները։

SQL trigger-ի իրական rollback փորձարկման համար առկա tools.smoke_mssql գործիքը ընդլայնված է արձագանքի ավելացման, կրկնության, փոխարինման ու չեղարկման ստուգումներով։ Այն ստեղծում է միայն թեստային fixture-ներ և վերջում ROLLBACK է անում։ Օգտագործեք փաստագրված --write-rollback --admin-id N --reviewed-behavior դրոշները միայն SQL trigger-ները ուսումնասիրելուց հետո։ IDENTITY բացեր կարող են մնալ։ HTTP authentication-ը այդ CLI գործիքով չի ստուգվում։

Իրական բազայի որևէ տվյալ այս փաթեթը պատրաստելիս չի փոփոխվել։
