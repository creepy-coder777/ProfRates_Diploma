from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from app.security import Principal, get_current_user
from app.student2.dependencies import get_db
from app.student2.tables import TABLES as T


def get_student(request: Request, user: Principal = Depends(get_current_user),
                db=Depends(get_db, scope='function')):
    if type(user.user_id) is not int or user.user_id <= 0 or user.is_admin:
        raise HTTPException(403, 'Մուտք գործեք ուսանողի հաշվով։')
    origin = request.headers.get('origin')
    if request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}:
        if request.headers.get('sec-fetch-site') == 'cross-site' or (
            origin and origin.rstrip('/') != str(request.base_url).rstrip('/')
        ):
            raise HTTPException(403, 'Այլ կայքից գործողությունն արգելված է։')
    u = T['Users']
    valid = db.execute(select(u.c.UserID).where(
        u.c.UserID == user.user_id, u.c.Status == 'Active', u.c.IsEmailVerified == True
    )).first()
    if not valid:
        raise HTTPException(403, 'Անհրաժեշտ է ակտիվ և հաստատված ուսանողի հաշիվ։')
    return user
