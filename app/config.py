from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from pydantic import SecretStr, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore")
    rating_edit_hours: int = Field(default=24, ge=1, le=720)
    auth_provider: str = ""
    audit_provider: str = ""
    db_server: str = ""
    db_name: str = ""
    db_driver: str = "ODBC Driver 17 for SQL Server"
    db_trusted_connection: bool = True
    db_user: str = ""
    db_password: SecretStr = SecretStr("")
    db_encrypt: bool = True
    db_trust_server_certificate: bool = False
    app_env: Literal['development','production'] = 'development'
    public_base_url: str = 'http://127.0.0.1:8000'
    cookie_secure: bool = False
    session_hours: int = Field(default=8,ge=1,le=24)
    remember_session_days: int = Field(default=14,ge=1,le=30)
    reset_minutes: int = Field(default=30,ge=1,le=120)
    verification_minutes: int = Field(default=60,ge=1,le=1440)
    mail_backend: Literal['local','smtp','disabled'] = 'local'
    local_mail_dir: str = 'var/mailbox'
    smtp_host: str = ''
    smtp_port: int = Field(default=587,ge=1,le=65535)
    smtp_from: str = ''
    smtp_user: str = ''
    smtp_password: SecretStr = SecretStr('')
    smtp_security: Literal['starttls','ssl'] = 'starttls'

    @model_validator(mode='after')
    def environment(self):
        url = urlsplit(self.public_base_url)
        if url.scheme not in {'http','https'} or not url.hostname or url.username or url.password or url.path not in {'','/'} or url.query or url.fragment:
            raise ValueError('PUBLIC_BASE_URL must be an origin without credentials, path, query or fragment')
        mail = Path(self.local_mail_dir)
        mail = mail if mail.is_absolute() else ROOT / mail
        if mail.resolve().is_relative_to((ROOT / 'frontend').resolve()):
            raise ValueError('Local mailbox must be outside frontend')
        if self.app_env == 'production':
            if self.mail_backend == 'local':
                raise ValueError('Local mailbox is forbidden in production')
            if not self.cookie_secure or url.scheme != 'https':
                raise ValueError('Production requires HTTPS and COOKIE_SECURE=true')
            if self.auth_provider:
                raise ValueError('Production uses the built-in database authentication provider')
        return self

@lru_cache
def get_settings() -> Settings:
    return Settings()
