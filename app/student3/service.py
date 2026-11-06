from datetime import timedelta
from app.student3.moderation import rating_status
from fastapi import HTTPException
from sqlalchemy import select, func, and_
from app.student2.tables import TABLES as T, summary, public_ratings
from app.student2 import service as shared


def eligibility_query(user_id):
    sc, co, le, progress, term = [
        T[n]
        for n in (
            "StudentCourses",
            "Courses",
            "Lecturers",
            "StudentAcademicProgress",
            "AcademicTerms",
        )
    ]
    return (
        select(co.c.CourseID, co.c.LecturerID, co.c.Name, progress.c.TermID)
        .select_from(
            sc.join(co, sc.c.CourseID == co.c.CourseID)
            .join(le, le.c.LecturerID == co.c.LecturerID)
            .join(
                progress,
                and_(
                    progress.c.UserID == sc.c.UserID,
                    progress.c.SemesterNumber == co.c.CurriculumSemesterNumber,
                ),
            )
            .join(term, term.c.TermID == progress.c.TermID)
        )
        .where(
            sc.c.UserID == user_id,
            progress.c.IsCurrent == True,
            co.c.IsActive == True,
            le.c.IsActive == True,
        )
    )


def check_eligibility(db, user_id, payload):
    co = T["Courses"]
    found = db.execute(
        eligibility_query(user_id).where(
            co.c.CourseID == payload.CourseID,
            co.c.LecturerID == payload.LecturerID,
            T["StudentAcademicProgress"].c.TermID == payload.TermID,
        )
    ).first()
    if not found:
        raise HTTPException(
            403, "Այս առարկան և կիսամյակը գնահատելու ուսումնական կապը բացակայում է։"
        )


def validate_answers(db, answers, expected=None):
    if expected is None:
        q = T["Questions"]
        expected = set(db.execute(select(q.c.QuestionID).where(q.c.IsActive == True)).scalars())
    if not expected or {a.QuestionID for a in answers} != expected:
        raise HTTPException(409, "Հարցաշարը փոխվել է կամ պատասխանները թերի են։ Վերբեռնեք էջը։")


def owned(db, ident, user_id):
    r = T["Ratings"]
    result = (
        db.execute(select(r).where(r.c.RatingID == ident, r.c.UserID == user_id)).mappings().first()
    )
    if result is None:
        # Same error for an unknown ID and another student's ID.
        raise HTTPException(404, "Գնահատումը չի գտնվել։")
    return dict(result)


def private_rating(db, ident, user_id):
    record = owned(db, ident, user_id)
    a = T["RatingAnswers"]
    record["answers"] = [
        dict(row)
        for row in db.execute(
            select(a.c.QuestionID, a.c.Score).where(a.c.RatingID == ident).order_by(a.c.QuestionID)
        ).mappings()
    ]
    db_now = db.execute(select(func.current_timestamp())).scalar_one()
    record['CanEditComment'] = (record['Status'] in {'Approved', 'Rejected'}
        and record['EditExpiry'] is not None and record['EditExpiry'] > db_now)
    # Explicit allowlist, even for the owner; never serialize the full Ratings row.
    keys = (
        "RatingID",
        "LecturerID",
        "CourseID",
        "TermID",
        "Comment",
        "Status",
        "CreatedAt",
        "UpdatedAt",
        "EditExpiry",
        "answers",
        "CanEditComment",
    )
    return {key: record[key] for key in keys}


def create_rating(db, actor, payload):
    check_eligibility(db, actor.user_id, payload)
    validate_answers(db, payload.answers)
    r = T["Ratings"]
    duplicate = db.execute(
        select(r.c.RatingID).where(
            r.c.UserID == actor.user_id,
            r.c.LecturerID == payload.LecturerID,
            r.c.CourseID == payload.CourseID,
        )
    ).first()
    if duplicate:
        raise HTTPException(409, "Այս առարկայի համար գնահատումն արդեն գոյություն ունի։")
    values = payload.model_dump(exclude={"answers"})
    # Existing EditExpiry stores the fixed comment-edit deadline; scores are immutable.
    values.update(
        UserID=actor.user_id,
        Status=rating_status(payload.Comment),
        ApprovedByAdminID=None,
        Likes=0,
        Dislikes=0,
        CreatedAt=func.current_timestamp(),
        UpdatedAt=func.current_timestamp(),
    )
    db_now = db.execute(select(func.current_timestamp())).scalar_one()
    values["CreatedAt"] = values["UpdatedAt"] = db_now
    values["EditExpiry"] = db_now + timedelta(hours=24)
    ident = db.execute(r.insert().values(**values)).inserted_primary_key[0]
    db.execute(
        T["RatingAnswers"].insert(),
        [dict(RatingID=ident, **a.model_dump()) for a in payload.answers],
    )
    shared.audit(db, actor, "Create", f"Ratings:{ident}")
    return private_rating(db, ident, actor.user_id)


def editable(db, ident, user_id, expected_updated_at):
    record = owned(db, ident, user_id)
    r = T["Ratings"]
    permitted = db.execute(
        select(r.c.RatingID).where(
            r.c.RatingID == ident,
            r.c.UserID == user_id,
            r.c.EditExpiry.is_not(None),
            r.c.EditExpiry > func.current_timestamp(),
        )
    ).first()
    if record["Status"] not in {"Approved", "Rejected"}:
        raise HTTPException(409, "Մեկնաբանությունը հնարավոր է խմբագրել հաստատումից կամ մերժումից հետո։")
    if not permitted or record["UpdatedAt"] != expected_updated_at:
        raise HTTPException(409, "Գնահատումը փոխվել է կամ փոփոխման հաստատված ժամկետը հասանելի չէ։")
    return record


def update_comment(db, actor, ident, comment, expected_updated_at):
    old = editable(db, ident, actor.user_id, expected_updated_at)
    from types import SimpleNamespace
    check_eligibility(db, actor.user_id, SimpleNamespace(**old))
    r = T['Ratings']
    db_now = db.execute(select(func.current_timestamp())).scalar_one()
    result = db.execute(r.update().where(
        r.c.RatingID == ident, r.c.UserID == actor.user_id,
        r.c.UpdatedAt == expected_updated_at, r.c.Status == old['Status'],
        r.c.EditExpiry > func.current_timestamp()).values(
            Comment=comment, Status=rating_status(comment), ApprovedByAdminID=None,
            UpdatedAt=db_now))
    if result.rowcount != 1:
        raise HTTPException(409, 'Գնահատումը փոխվել է կամ մեկնաբանության խմբագրման ժամկետն ավարտվել է։')
    # Do not change answers or extend EditExpiry when the student edits text.
    shared.audit(db, actor, 'CommentUpdated', f'Ratings:{ident}')
    return private_rating(db, ident, actor.user_id)


def edit_rating(db, actor, ident, payload):
    # Compatibility with old clients: accept only the identical stored answers/context.
    old = owned(db, ident, actor.user_id)
    if any(old[k] != getattr(payload, k) for k in ('LecturerID','CourseID','TermID')):
        raise HTTPException(409, 'Գնահատման դասախոսը, առարկան և կիսամյակը փոխել չի կարելի։')
    a = T['RatingAnswers']
    stored = dict(db.execute(select(a.c.QuestionID,a.c.Score).where(a.c.RatingID == ident)).all())
    submitted = {answer.QuestionID:answer.Score for answer in payload.answers}
    if submitted != stored:
        raise HTTPException(409, 'Ուղարկված միավորները խմբագրել չի կարելի։')
    return update_comment(db, actor, ident, payload.Comment, payload.expected_updated_at)


def delete_rating(db, actor, ident, expected_updated_at):
    owned(db, ident, actor.user_id)
    # A delete/re-create cycle must not bypass the immutable-score rule.
    raise HTTPException(409, 'Ուղարկված գնահատումը ջնջել չի կարելի։')


def statistics(db, ident):
    lecturer = shared.row(db, T["Lecturers"], "LecturerID", ident)
    if not lecturer["IsActive"]:
        raise HTTPException(404, "Դասախոսը չի գտնվել։")
    result = db.execute(select(summary).where(summary.c.LecturerID == ident)).mappings().first()
    if result is None:
        raise HTTPException(503, "Վարկանիշի SQL աղբյուրը հասանելի չէ։")
    a, r = T["RatingAnswers"], T["Ratings"]
    counts = dict(
        db.execute(
            select(a.c.Score, func.count())
            .select_from(a.join(r, a.c.RatingID == r.c.RatingID))
            .where(r.c.LecturerID == ident, r.c.Status == "Approved")
            .group_by(a.c.Score)
        ).all()
    )
    # This is the distribution of individual question answers, not rounded rating averages.
    return {
        **dict(result),
        "source": "dbo.vwLecturerRatingSummary",
        "distribution_unit": "question_answers",
        "distribution": [{"score": score, "count": counts.get(score, 0)} for score in range(1, 6)],
    }
