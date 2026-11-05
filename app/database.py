from functools import lru_cache
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from app.config import Settings, get_settings

class DatabaseNotConfigured(RuntimeError):
    pass

def quote_odbc(value: str) -> str:
    # ODBC արժեքները փակագծելը պաշտպանում է նաև ; և } պարունակող գաղտնաբառերը։
    return "{" + value.replace("}", "}}") + "}"

def connection_string(s: Settings) -> str:
    if not s.db_server.strip() or not s.db_name.strip():
        raise DatabaseNotConfigured("Լրացրեք DB_SERVER և DB_NAME արժեքները .env ֆայլում։")
    parts = [f"DRIVER={quote_odbc(s.db_driver)}", f"SERVER={quote_odbc(s.db_server)}",
             f"DATABASE={quote_odbc(s.db_name)}",
             f"Encrypt={'yes' if s.db_encrypt else 'no'}",
             f"TrustServerCertificate={'yes' if s.db_trust_server_certificate else 'no'}"]
    if s.db_trusted_connection:
        parts.append("Trusted_Connection=yes")
    else:
        if not s.db_user or not s.db_password.get_secret_value():
            raise DatabaseNotConfigured("Լրացրեք տեղային SQL մուտքի տվյալները։")
        parts += [f"UID={quote_odbc(s.db_user)}", f"PWD={quote_odbc(s.db_password.get_secret_value())}"]
    return ";".join(parts)

@lru_cache
def get_engine():
    # Ոչ create_all, ոչ migration. Օգտագործում ենք միայն առկա բազան։
    url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_string(get_settings())})
    return create_engine(url, pool_pre_ping=True, hide_parameters=True, connect_args={"timeout": 5})
