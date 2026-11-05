from sqlalchemy import select,func
from app.student2.tables import TABLES as T
from tools.smoke_mssql import exercise

def test_fixture_plan_rolls_back_without_changing_existing_rows(database):
    with database.connect() as db:
        before={n:db.execute(select(func.count()).select_from(t)).scalar_one()for n,t in T.items()}
    stages=[]
    with database.connect() as db:
        transaction=db.begin()
        try:
            created=exercise(db,1,'S2TEST_unit',stages.append)
            assert len(created)>=12
            assert 'question_version_and_answer_history'in stages
            assert 'approve_reject_live_views_idempotency'in stages
        finally:transaction.rollback()
    with database.connect() as db:
        after={n:db.execute(select(func.count()).select_from(t)).scalar_one()for n,t in T.items()}
    assert after==before
    assert 'reaction_sql_trigger_insert_switch_clear' in stages
    assert len(stages)==7
