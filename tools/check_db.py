from sqlalchemy import text
from app.database import get_engine

def main():
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
        print("SQL Server-ի միացումը հաջողվեց։")
        return 0
    except Exception:
        print("Միացումը չհաջողվեց։ Ստուգեք .env-ը, SQL Server ծառայությունը, ODBC driver-ը և մուտքի իրավունքը։")
        print("Գաղտնաբառը կամ ամբողջ connection string-ը մի ուղարկեք զրույցում։")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
