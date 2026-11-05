"""Trusted registration roster, managed by administrators; never a public lookup."""
from sqlalchemy import Table, Column, Unicode, Integer, Boolean, select, func
from fastapi import HTTPException
from app.student2.tables import metadata, TABLES as T

roster = Table('StudentRoster', metadata,
    Column('Email', Unicode(255), primary_key=True),
    Column('FirstName', Unicode(100), nullable=False),
    Column('LastName', Unicode(100), nullable=False),
    Column('GroupID', Integer, nullable=False),
    Column('IsActive', Boolean, nullable=False),
    Column('UserID', Integer, nullable=True))
T['StudentRoster'] = roster


def candidate(db, email):
    g, sp, ch = [T[n] for n in ('StudentGroups','Specializations','Chairs')]
    item = db.execute(select(roster).select_from(roster.join(g, g.c.GroupID == roster.c.GroupID)
        .join(sp, sp.c.SpecializationID == g.c.SpecializationID)
        .join(ch, ch.c.ChairID == sp.c.ChairID)).where(
            func.lower(roster.c.Email) == email, roster.c.IsActive == True,
            g.c.IsActive == True, sp.c.IsActive == True, ch.c.IsActive == True)).mappings().first()
    if not item or item['UserID'] is not None:
        raise HTTPException(422, 'Registration is unavailable. Contact the university administrator.')
    return item


def check_group(db, ident):
    g, sp, ch = [T[n] for n in ('StudentGroups','Specializations','Chairs')]
    found = db.execute(select(g.c.GroupID).select_from(g.join(sp, sp.c.SpecializationID == g.c.SpecializationID)
        .join(ch, ch.c.ChairID == sp.c.ChairID)).where(g.c.GroupID == ident,
            g.c.IsActive == True, sp.c.IsActive == True, ch.c.IsActive == True)).first()
    if not found:
        raise HTTPException(422, 'Choose an active group belonging to an active specialization and chair.')
