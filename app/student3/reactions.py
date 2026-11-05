"""One persisted reaction per verified student and published comment."""

from fastapi import HTTPException
from sqlalchemy import select
from app.student2.tables import TABLES as T
from app.student2.service import audit


def state(db, actor, ident, value=None, write=False):
    r, reactions = T["Ratings"], T["RatingReactions"]
    statement = select(r.c.RatingID, r.c.Likes, r.c.Dislikes).where(
        r.c.RatingID == ident, r.c.Status == "Approved", r.c.Comment.is_not(None), r.c.Comment != ""
    )
    if write:
        statement = statement.with_hint(r, "WITH (UPDLOCK, HOLDLOCK)", dialect_name="mssql")
    rating = db.execute(statement).mappings().first()
    if rating is None:
        raise HTTPException(404, "Հրապարակված մեկնաբանությունը չի գտնվել։")
    condition = (reactions.c.RatingID == ident) & (reactions.c.UserID == actor.user_id)
    old = db.execute(select(reactions.c.Reaction).where(condition)).scalar_one_or_none()
    if write and old != value:
        if value is None:
            db.execute(reactions.delete().where(condition))
        elif old is None:
            db.execute(
                reactions.insert().values(RatingID=ident, UserID=actor.user_id, Reaction=value)
            )
        else:
            db.execute(reactions.update().where(condition).values(Reaction=value))
        # SQL trigger alone maintains counters, including the original anonymous totals.
        audit(db, actor, "React", f"Ratings:{ident}")
    current = (
        db.execute(select(r.c.Likes, r.c.Dislikes).where(r.c.RatingID == ident)).mappings().one()
    )
    return {"RatingID": ident, **dict(current), "reaction": value if write else old}
