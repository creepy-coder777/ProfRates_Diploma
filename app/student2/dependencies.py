from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DataError, SQLAlchemyError
from app.database import get_engine, DatabaseNotConfigured
from app.security import require_admin, Principal
from app.student2.tables import TABLES


def get_db():
    try:
        # Պաշտպանում է նաև ստուգումից մինչև գրառում միջակայքը զուգահեռ հարցումներից։
        with get_engine().connect().execution_options(isolation_level='SERIALIZABLE') as connection:
            with connection.begin():
                yield connection
    except HTTPException:
        raise
    except IntegrityError:
        raise HTTPException(409,'Կրկնվող արժեք կամ բազայի կապերի/սահմանափակումների խախտում։') from None
    except DataError:
        raise HTTPException(422,'Տվյալը չի համապատասխանում բազայի դաշտի սահմանափակումներին։') from None
    except (SQLAlchemyError,DatabaseNotConfigured,ImportError):
        raise HTTPException(503,'Բազայի գործողությունը չի ավարտվել։ Ստուգեք միացումը և կառուցվածքի համապատասխանությունը։') from None


def get_actor(request: Request, user: Principal = Depends(require_admin), db=Depends(get_db,scope="function")):
    origin=request.headers.get('origin')
    if request.method in {'POST','PUT','PATCH','DELETE'} and origin and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
        raise HTTPException(403,'Հարցման աղբյուրը թույլատրված չէ։')
    if not user.admin_id or not db.execute(select(TABLES['Admins'].c.AdminID).where(TABLES['Admins'].c.AdminID==user.admin_id)).first():
        raise HTTPException(403,'Պահանջվում է առկա Admins գրառմանը կապված նույնականացում։')
    return user
