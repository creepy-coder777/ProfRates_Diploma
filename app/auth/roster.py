"""Validate existing educational groups. No registration roster is required."""
from sqlalchemy import select
from fastapi import HTTPException
from app.student2.tables import TABLES as T


def check_group(db, ident):
    g, sp, ch = [T[n] for n in ('StudentGroups','Specializations','Chairs')]
    found = db.execute(select(g.c.GroupID).select_from(g.join(sp, sp.c.SpecializationID == g.c.SpecializationID)
        .join(ch, ch.c.ChairID == sp.c.ChairID)).where(g.c.GroupID == ident,
            g.c.IsActive == True, sp.c.IsActive == True, ch.c.IsActive == True)).first()
    if not found:
        raise HTTPException(422, 'Choose an active group belonging to an active specialization and chair.')
