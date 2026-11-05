"""Only the explicit 03 migration adds these objects in a real SQL Server."""
from sqlalchemy import Table, Column, Integer, String, UnicodeText, Boolean, DateTime, CheckConstraint
from app.student2.tables import metadata, TABLES

sessions = Table('AuthSessions', metadata,
    Column('SessionHash', String(64), primary_key=True),
    Column('UserID', Integer), Column('AdminID', Integer),
    Column('CSRFHash', String(64), nullable=False),
    Column('CreatedAt', DateTime, nullable=False), Column('ExpiresAt', DateTime, nullable=False),
    CheckConstraint('(UserID IS NOT NULL AND AdminID IS NULL) OR (UserID IS NULL AND AdminID IS NOT NULL)', name='CK_AuthSessions_Actor'),
    implicit_returning=False)
limits = Table('AuthRateLimits', metadata,
    Column('KeyHash', String(64), primary_key=True),
    Column('WindowStart', Integer, nullable=False), Column('Attempts', Integer, nullable=False),
    implicit_returning=False)
TABLES['AuthSessions'] = sessions
TABLES['AuthRateLimits'] = limits
