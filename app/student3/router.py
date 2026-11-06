from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from app.student2.dependencies import get_db, get_actor
from app.student2.router import pagination
from app.student2.service import page
from app.student2.tables import TABLES as T, public_ratings, admin_ratings
from app.student3.dependencies import get_student
from app.student3.schemas import RatingInput, RatingEdit, CommentEdit, PrivateRating, PublicRating
from app.student3 import service as svc

router = APIRouter(prefix='/api', tags=['Student 3: ratings and statistics'])


@router.get('/admin/rating-queue')
def rating_queue(p=Depends(pagination), actor=Depends(get_actor), db=Depends(get_db, scope='function')):
    # Moderation uses the existing PUT /api/admin/comments/{ident}/moderation.
    return page(db, select(admin_ratings), admin_ratings.c.RatingID, *p)


@router.get('/admin/lecturers/{ident}/rating-statistics')
def admin_statistics(ident: int, actor=Depends(get_actor), db=Depends(get_db, scope='function')):
    from sqlalchemy import func
    r = T['Ratings']
    result = svc.statistics(db, ident)
    counts = dict(db.execute(select(r.c.Status, func.count()).where(
        r.c.LecturerID == ident, r.c.Comment.is_not(None), r.c.Comment != ''
    ).group_by(r.c.Status)).all())
    result['comment_status_counts'] = {status: counts.get(status, 0) for status in ('Pending', 'Approved', 'Rejected')}
    return result


@router.get('/me/rating-options')
def options(actor=Depends(get_student), db=Depends(get_db, scope='function')):
    return {'items': [dict(r) for r in db.execute(svc.eligibility_query(actor.user_id)).mappings()]}


@router.get('/me/ratings')
def mine(p=Depends(pagination), actor=Depends(get_student), db=Depends(get_db, scope='function')):
    r = T['Ratings']
    result = page(db, select(r.c.RatingID).where(r.c.UserID == actor.user_id).order_by(r.c.RatingID.desc()), r.c.RatingID, *p)
    result['items'] = [svc.private_rating(db, item['RatingID'], actor.user_id) for item in result['items']]
    return result


@router.get('/me/ratings/{ident}', response_model=PrivateRating)
def my_rating(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    return svc.private_rating(db, ident, actor.user_id)


@router.post('/ratings', status_code=201, response_model=PrivateRating)
def create(payload: RatingInput, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    return svc.create_rating(db, actor, payload)


@router.get('/me/ratings/{ident}/questions')
def historical_questions(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    svc.owned(db, ident, actor.user_id)
    q, a = T['Questions'], T['RatingAnswers']
    statement = select(q).join(a, a.c.QuestionID == q.c.QuestionID).where(a.c.RatingID == ident)
    return {'items': [dict(row) for row in db.execute(statement.order_by(q.c.SortOrder, q.c.QuestionID)).mappings()]}


@router.put('/ratings/{ident}', response_model=PrivateRating)
def edit(ident: int, payload: RatingEdit, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    return svc.edit_rating(db, actor, ident, payload)


@router.patch('/ratings/{ident}/comment', response_model=PrivateRating)
def edit_comment(ident: int, payload: CommentEdit, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    return svc.update_comment(db, actor, ident, payload.Comment, payload.expected_updated_at)


@router.delete('/ratings/{ident}')
def delete(ident: int, expected_updated_at: datetime = Query(...),
           actor=Depends(get_student), db=Depends(get_db, scope='function')):
    return svc.delete_rating(db, actor, ident, expected_updated_at)


@router.get('/lecturers/{ident}/ratings')
def public_list(ident: int, p=Depends(pagination), db=Depends(get_db, scope='function')):
    svc.statistics(db, ident)
    result = page(db, select(public_ratings).where(public_ratings.c.LecturerID == ident), public_ratings.c.RatingID, *p)
    result['items'] = [PublicRating.model_validate(item).model_dump() for item in result['items']]
    return result


@router.get('/lecturers/{ident}/statistics')
def statistics(ident: int, db=Depends(get_db, scope='function')):
    return svc.statistics(db, ident)


@router.get('/ratings/{ident}/reaction')
@router.get('/ratings/{ident}/like')
def reaction_state(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    from app.student3.reactions import state
    return state(db, actor, ident)


@router.put('/ratings/{ident}/like')
def like(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    from app.student3.reactions import state
    return state(db, actor, ident, 1, True)


@router.put('/ratings/{ident}/dislike')
def dislike(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    from app.student3.reactions import state
    return state(db, actor, ident, -1, True)


@router.delete('/ratings/{ident}/reaction')
def clear_reaction(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    from app.student3.reactions import state
    return state(db, actor, ident, None, True)


@router.delete('/ratings/{ident}/like')
def clear_like(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    from app.student3.reactions import state
    current = state(db, actor, ident)
    return state(db, actor, ident, None, True) if current['reaction'] == 1 else current


@router.delete('/ratings/{ident}/dislike')
def clear_dislike(ident: int, actor=Depends(get_student), db=Depends(get_db, scope='function')):
    from app.student3.reactions import state
    current = state(db, actor, ident)
    return state(db, actor, ident, None, True) if current['reaction'] == -1 else current


@router.get('/rankings')
def rankings(lang: str = Query("hy", pattern="^(hy|en)$"),db=Depends(get_db, scope='function')):
    from sqlalchemy import text
    # Reuse the supplied SQL Server Bayesian procedure with its own defaults.
    rows = db.execute(text('EXEC dbo.uspLecturerRankings')).mappings().all()
    from app.student2.service import lecturer_departments
    lecturers = {row['LecturerID']: dict(row) for row in db.execute(select(T['Lecturers']).where(T['Lecturers'].c.IsActive == True)).mappings()}
    items = [{**lecturers[row['LecturerID']], **dict(row)} for row in rows if row['LecturerID'] in lecturers]
    lecturer_departments(db, items)
    from app.localization import lecturer_page
    return lecturer_page({'items': items, 'source': 'dbo.uspLecturerRankings'},lang)
