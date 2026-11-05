"""Read-only structural check; does not impose a rating publication policy."""
from sqlalchemy import text
from app.database import get_engine

def missing_objects(row, disabled):
    labels = {
        'reactions': 'dbo.RatingReactions table',
        'reaction_trigger': 'dbo.tr_RatingReactions_Counters trigger',
        'summary_sql': 'dbo.vwLecturerRatingSummary readable definition',
        'rankings': 'dbo.uspLecturerRankings procedure',
    }
    problems = [label for key, label in labels.items() if row[key] is None]
    if row['reaction_trigger'] is not None and disabled is not False and disabled != 0:
        problems.append('reaction trigger is disabled or its state is unavailable')
    return problems

def main():
    try:
        with get_engine().connect() as db:
            row = db.execute(text("""SELECT
                OBJECT_ID('dbo.RatingReactions','U') AS reactions,
                OBJECT_ID('dbo.tr_RatingReactions_Counters','TR') AS reaction_trigger,
                OBJECT_DEFINITION(OBJECT_ID('dbo.vwLecturerRatingSummary')) AS summary_sql,
                OBJECT_ID('dbo.uspLecturerRankings','P') AS rankings""")).mappings().one()
            disabled = db.execute(text("SELECT is_disabled FROM sys.triggers WHERE object_id=OBJECT_ID('dbo.tr_RatingReactions_Counters')")).scalar_one_or_none()
        problems = missing_objects(row, disabled)
        print('STUDENT3 SQL STRUCTURE: ' + ('READY' if not problems else 'CHECK REQUIRED'))
        for problem in problems:
            print('CHECK: ' + problem)
        print('Read-only metadata check; trigger execution and rating business rules are not tested.')
        print('Approved-only filtering is allowed. Do not overwrite existing rating views just to pass this check.')
        return 1 if problems else 0
    except Exception:
        print('Cannot inspect SQL metadata. Check connection and VIEW DEFINITION permission.')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
