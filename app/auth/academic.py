"""Provision existing curriculum links without inventing courses or changing history."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, exists
from app.student2.tables import TABLES as T


def current_term(db, today):
    terms = list(db.execute(select(T['AcademicTerms'])).mappings())
    dated = [t for t in terms if t['StartsOn'] and t['EndsOn']
             and t['StartsOn'] <= today <= t['EndsOn']]
    if len(dated) == 1:
        return dated[0]
    if dated:
        return None
    # Legacy periods have no dates. Autumn begins in September, spring in February.
    # Configured dates always take precedence; never reuse an expired dated period.
    year = today.year if today.month >= 9 else today.year - 1
    number = 1 if today.month >= 9 or today.month == 1 else 2
    matches = [t for t in terms if t['AcademicYearStart'] == year
               and t['TermNumber'] == number
               and not t['StartsOn'] and not t['EndsOn']]
    return matches[0] if len(matches) == 1 else None


def sync_student(db, user_id, today=None):
    today = today or datetime.now(timezone(timedelta(hours=4))).date()
    u, g, sp, ch = [T[n] for n in ('Users', 'StudentGroups', 'Specializations', 'Chairs')]
    student = db.execute(
        select(g.c.EnrollmentYear, g.c.SpecializationID)
        .select_from(u.join(g, u.c.GroupID == g.c.GroupID)
                     .join(sp, sp.c.SpecializationID == g.c.SpecializationID)
                     .join(ch, ch.c.ChairID == sp.c.ChairID))
        .where(u.c.UserID == user_id, u.c.Status == 'Active', g.c.IsActive == True,
               sp.c.IsActive == True, ch.c.IsActive == True)
    ).mappings().first()
    if student is None:
        return 'group-unavailable'
    term = current_term(db, today)
    if term is None:
        return 'term-unconfigured'
    if term['TermNumber'] not in (1, 2):
        return 'term-unconfigured'
    progress = T['StudentAcademicProgress']
    target = db.execute(select(progress).where(
        progress.c.UserID == user_id, progress.c.TermID == term['TermID']
    )).mappings().first()
    semester = (target['SemesterNumber'] if target else
                (term['AcademicYearStart'] - student['EnrollmentYear']) * 2 + term['TermNumber'])
    # Do not mark an account graduated or clamp an out-of-range student to semester 8.
    if semester not in range(1, 9):
        return 'academic-review-required'
    if not db.execute(select(T['AcademicSemesters'].c.SemesterNumber).where(
        T['AcademicSemesters'].c.SemesterNumber == semester
    )).first():
        return 'semester-unconfigured'
    db.execute(progress.update().where(progress.c.UserID == user_id,
                                       progress.c.IsCurrent == True,
                                       progress.c.TermID != term['TermID']).values(IsCurrent=False))
    if target:
        if not target['IsCurrent']:
            db.execute(progress.update().where(progress.c.UserID == user_id,
                       progress.c.TermID == term['TermID']).values(IsCurrent=True))
    else:
        db.execute(progress.insert().values(UserID=user_id, TermID=term['TermID'],
                                             SemesterNumber=semester, IsCurrent=True))
    courses, lecturers, links = [T[n] for n in ('Courses', 'Lecturers', 'StudentCourses')]
    missing = list(db.execute(
        select(courses.c.CourseID).select_from(courses.join(
            lecturers, lecturers.c.LecturerID == courses.c.LecturerID))
        .where(courses.c.SpecializationID == student['SpecializationID'],
               courses.c.CurriculumSemesterNumber == semester,
               courses.c.IsActive == True, lecturers.c.IsActive == True,
               ~exists(select(1).select_from(links).where(
                   links.c.UserID == user_id, links.c.CourseID == courses.c.CourseID)))
    ).scalars())
    if missing:
        db.execute(links.insert(), [dict(UserID=user_id, CourseID=ident,
                   EnrolledAt=datetime.now(timezone.utc).replace(tzinfo=None)) for ident in missing])
    available = db.execute(select(courses.c.CourseID).select_from(courses.join(
        lecturers, lecturers.c.LecturerID == courses.c.LecturerID)).where(
            courses.c.SpecializationID == student['SpecializationID'],
            courses.c.CurriculumSemesterNumber == semester,
            courses.c.IsActive == True, lecturers.c.IsActive == True)).first()
    return 'ready' if available else 'curriculum-missing'
