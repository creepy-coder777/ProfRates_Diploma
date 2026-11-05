"""Կարդում է միայն metadata՝ առանց ուսանողների կամ գնահատումների տվյալների։"""
import json
from pathlib import Path
from sqlalchemy import text
from app.database import get_engine

QUERIES = {
    'database': 'SELECT DB_NAME() AS database_name, HAS_PERMS_BY_NAME(DB_NAME(), \'DATABASE\', \'VIEW DEFINITION\') AS can_view_definition',
    'objects': '''SELECT s.name AS schema_name, o.name, o.type_desc, o.object_id
        FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
        WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name''',
    'columns': '''SELECT s.name AS schema_name, o.name AS object_name, c.column_id, c.name,
        ty.name AS type_name,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity,
        c.is_computed,cc.definition AS computed_definition,dc.definition AS default_definition
        FROM sys.columns c JOIN sys.objects o ON c.object_id=o.object_id
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        LEFT JOIN sys.computed_columns cc ON cc.object_id=c.object_id AND cc.column_id=c.column_id
        LEFT JOIN sys.default_constraints dc ON dc.object_id=c.default_object_id
        WHERE o.is_ms_shipped=0 ORDER BY s.name,o.name,c.column_id''',
    'foreign_keys': '''SELECT fk.name,OBJECT_SCHEMA_NAME(fk.parent_object_id) AS source_schema,
        OBJECT_NAME(fk.parent_object_id) AS source_table,pc.name AS source_column,
        OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS target_schema,
        OBJECT_NAME(fk.referenced_object_id) AS target_table,rc.name AS target_column,
        fkc.constraint_column_id,fk.delete_referential_action_desc,fk.update_referential_action_desc,
        fk.is_disabled,fk.is_not_trusted
        FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fkc ON fk.object_id=fkc.constraint_object_id
        JOIN sys.columns pc ON pc.object_id=fkc.parent_object_id AND pc.column_id=fkc.parent_column_id
        JOIN sys.columns rc ON rc.object_id=fkc.referenced_object_id AND rc.column_id=fkc.referenced_column_id''',
    'indexes': '''SELECT OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,OBJECT_NAME(i.object_id) AS table_name,
        i.name,i.is_unique,i.is_primary_key,i.is_unique_constraint,i.is_disabled,i.filter_definition,
        c.name AS column_name,ic.key_ordinal,ic.is_included_column,ic.is_descending_key
        FROM sys.indexes i JOIN sys.index_columns ic ON i.object_id=ic.object_id AND i.index_id=ic.index_id
        JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        JOIN sys.objects o ON o.object_id=i.object_id WHERE o.is_ms_shipped=0''',
    'checks': '''SELECT OBJECT_SCHEMA_NAME(parent_object_id) AS schema_name,
        OBJECT_NAME(parent_object_id) AS table_name,name,definition,is_disabled,is_not_trusted FROM sys.check_constraints''',
    'modules': '''SELECT OBJECT_SCHEMA_NAME(m.object_id) AS schema_name,o.name,o.type_desc,m.definition
        FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id WHERE o.is_ms_shipped=0''',
    'triggers': '''SELECT name,OBJECT_SCHEMA_NAME(parent_id) AS parent_schema,
        OBJECT_NAME(parent_id) AS parent_object,is_disabled,is_instead_of_trigger FROM sys.triggers WHERE is_ms_shipped=0''',
    'parameters': '''SELECT OBJECT_SCHEMA_NAME(p.object_id) AS schema_name,OBJECT_NAME(p.object_id) AS object_name,
        p.parameter_id,p.name,TYPE_NAME(p.user_type_id) AS type_name,p.max_length,p.is_output
        FROM sys.parameters p JOIN sys.objects o ON o.object_id=p.object_id WHERE o.is_ms_shipped=0''',
}

def collect_metadata(connection):
    return {label:[dict(row) for row in connection.execute(text(query)).mappings()] for label,query in QUERIES.items()}

def main():
    try:
        with get_engine().connect() as connection:
            result = collect_metadata(connection)
        if result['database'][0]['can_view_definition'] != 1:
            print('Արտահանումը չի պահպանվել. անհրաժեշտ է DBA-ի միջոցով ստանալ ամբողջական VIEW DEFINITION հասանելիություն։')
            return 1
        path = Path('exports/schema_metadata.json')
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
        print(f'Պահպանված է՝ {path}։ Արտահանումը տվյալների տողեր չի պարունակում։')
        if any(row['definition'] is None for row in result['modules']):
            print('Զգուշացում՝ որոշ module-ների սահմանումները հասանելի չեն կամ կոդավորված են։')
        return 0
    except Exception:
        print('Արտահանումը ձախողվեց։ Ստուգեք միացումը և metadata դիտելու իրավունքը։')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
