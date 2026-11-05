"""Բացահայտ mapping՝ 21.10.2026 SQL արտահանումից և 03_auth_accounts.sql-ից. DDL չի գործարկվում։"""
import json
from sqlalchemy import MetaData, Table, Column, Integer, SmallInteger, String, Unicode, UnicodeText, Boolean, DateTime, Date, Numeric
from app.config import ROOT

metadata = MetaData(schema="dbo")
TABLES = {}
for name, fields in json.loads((ROOT / "docs/verified_schema.json").read_text()).items():
    columns = []
    for f in fields:
        kind = f['type']; size = f['size']
        length = int(size[1:-1]) if size and size != '(max)' else None
        typ = {'int': Integer, 'smallint': SmallInteger, 'tinyint': SmallInteger, 'bit': Boolean,
               'datetime': DateTime, 'date': Date}.get(kind)
        if typ: typ = typ()
        elif kind == 'nvarchar': typ = Unicode(length) if length else UnicodeText()
        else: typ = String(length)
        # Այս mapping-ի բոլոր ինքնաճող ID-ները իրական առաջնային բանալիներ են։
        pk = f['identity'] or (name == 'AcademicSemesters' and f['name'] == 'SemesterNumber')
        columns.append(Column(f['name'], typ, primary_key=pk, nullable=f['nullable'], default=False if name=='Admins' and f['name']=='IsEmailVerified' else 'reset' if name=='PasswordResets' and f['name']=='Purpose' else None, autoincrement=True if f['identity'] else False))
    TABLES[name] = Table(name, metadata, *columns, implicit_returning=False)

summary = Table('vwLecturerRatingSummary', metadata,
    Column('LecturerID', Integer), Column('TotalRatings', Integer),
    Column('TotalAnswers', Integer), Column('AverageScore', Numeric(5,2)))
admin_ratings = Table('vw_Ratings_Admin', metadata, *[
    Column(n, Integer if n in ['RatingID','LecturerID'] else Numeric(5,2) if n == 'OverallScore' else DateTime if n=='CreatedAt' else UnicodeText())
    for n in ['RatingID','LecturerID','LecturerName','StudentName','StudentGroup','OverallScore','Comment','Status','CreatedAt']])
public_ratings = Table('vw_Ratings_Public',metadata,Column('RatingID',Integer),Column('LecturerID',Integer),
 Column('OverallScore',Numeric(5,2)),Column('Comment',UnicodeText()),Column('CreatedAt',DateTime),Column('Likes',Integer),Column('Dislikes',Integer))

TABLES['RatingReactions'] = Table('RatingReactions', metadata,
    Column('RatingID', Integer, primary_key=True, autoincrement=False),
    Column('UserID', Integer, primary_key=True, autoincrement=False),
    Column('Reaction', SmallInteger, nullable=False), implicit_returning=False)
