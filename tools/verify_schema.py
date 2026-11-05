"""Read-only SQL Server contract verification. No DDL, migration or DML."""
import argparse
import json
import re
from pathlib import Path
from sqlalchemy import text
from app.config import ROOT
from app.database import get_engine
from tools.export_schema import collect_metadata

CONTRACT_PATH=ROOT/'docs/schema_contract.json'

def normalize_filter(value):
    return re.sub(r'[\s\[\]()]','',value or '').lower()

def normalized_definition(value):
    # Text comparison only; this does NOT prove equivalent runtime behavior.
    return re.sub(r'\s+',' ',(value or '').replace('\r\n','\n')).strip()

def compare_metadata(snapshot,contract):
    errors=[];warnings=[];checked=0
    full=bool(snapshot.get('database') and snapshot['database'][0].get('can_view_definition')==1)
    if not full:errors.append('Metadata-ը ամբողջական չէ. անհրաժեշտ է բազայի VIEW DEFINITION իրավունքը։')
    columns={(r['schema_name'],r['object_name'],r['name']):r for r in snapshot.get('columns',[])}
    objects={(r['schema_name'],r['name']):r['type_desc'] for r in snapshot.get('objects',[])}
    for name,spec in [*contract['tables'].items(),*((n,{'columns':cols}) for n,cols in contract['view_columns'].items())]:
        expected_kind='USER_TABLE' if name in contract['tables'] else 'VIEW'
        if objects.get(('dbo',name))!=expected_kind:errors.append(f'dbo.{name}: սպասվում է {expected_kind}։')
        for column,expected in spec['columns'].items():
            actual=columns.get(('dbo',name,column));label=f'dbo.{name}.{column}'
            if actual is None:errors.append(label+': դաշտը բացակայում է։');continue
            for attr,value in expected.items():
                checked+=1
                actual_value=actual.get(attr)
                # numeric and decimal are SQL Server synonyms.
                if attr=='type_name':
                    canon=lambda v:'decimal' if str(v).lower() in {'decimal','numeric'} else str(v).lower()
                    matches=canon(actual_value)==canon(value)
                else:matches=actual_value==value
                if not matches:errors.append(f'{label}: {attr}՝ սպասվող {value!r}, իրական {actual_value!r}։')
    for (schema,table,name),column in columns.items():
        if schema=='dbo' and table in contract['tables'] and name not in contract['tables'][table]['columns']:
            if not column.get('is_nullable') and not column.get('is_identity') and not column.get('is_computed') and column.get('default_definition') is None:
                errors.append(f'dbo.{table}.{name}: արտահանման մեջ չեղած պարտադիր դաշտ՝ առանց default-ի։')
            else:warnings.append(f'dbo.{table}.{name}: լրացուցիչ դաշտ, որը մեր mapping-ում չկա։')
    indexes={}
    for r in snapshot.get('indexes',[]):
        if r['schema_name']!='dbo' or r.get('is_included_column'):continue
        key=(r['table_name'],r['name']);indexes.setdefault(key,[]).append(r)
    grouped={}
    for (table,name),rows in indexes.items():
        rows=sorted(rows,key=lambda r:r['key_ordinal'])
        item={'columns':[r['column_name'] for r in rows if r['key_ordinal']>0],
              'primary':bool(rows[0]['is_primary_key']),'unique':bool(rows[0]['is_unique']),
              'disabled':bool(rows[0].get('is_disabled',False)),'filter':rows[0].get('filter_definition')}
        grouped.setdefault(table,[]).append(item)
    actual_fk={}
    for r in snapshot.get('foreign_keys',[]):
        if r['source_schema']=='dbo':actual_fk.setdefault((r['source_table'],r['name']),[]).append(r)
    for name,spec in contract['tables'].items():
        ix=grouped.get(name,[]);checked+=1
        if not any(i['primary'] and not i['disabled'] and i['columns']==spec['primary_key'] for i in ix):
            errors.append(f'dbo.{name}: հիմնական բանալին բացակայում է կամ չի համապատասխանում {spec["primary_key"]}։')
        for key in spec['unique_keys']:
            checked+=1
            if not any(i['unique'] and not i['disabled'] and i['columns']==key['columns'] and normalize_filter(i['filter'])==normalize_filter(key['filter']) for i in ix):
                errors.append(f'dbo.{name}: UNIQUE բանալին չի համապատասխանում {key}։')
        for fk in spec['foreign_keys']:
            checked+=1;matched=False
            for (table,_),rows in actual_fk.items():
                if table!=name:continue
                rows=sorted(rows,key=lambda r:r['constraint_column_id'])
                if ([r['source_column']for r in rows]==fk['source_columns'] and
                    [r['target_column']for r in rows]==fk['target_columns'] and
                    rows[0]['target_schema']==fk['target_schema'] and rows[0]['target_table']==fk['target_table'] and
                    not any(r['is_disabled'] or r['is_not_trusted'] for r in rows)):
                    matched=True;break
            if not matched:errors.append(f'dbo.{name}: FK բացակայում է, ապաակտիվացված է կամ վստահելի չէ՝ {fk}։')
    modules={(r['schema_name'],r['name']):r.get('definition') for r in snapshot.get('modules',[])}
    definitions={}
    for name,source in contract['view_definitions'].items():
        current=modules.get(('dbo',name))
        definitions[name]='unavailable' if current is None else 'text_match' if normalized_definition(current)==normalized_definition(source) else 'text_differs'
        if definitions[name]!='text_match':warnings.append(f'dbo.{name}: view-ի սահմանումը {definitions[name]} է. անհրաժեշտ է առանձին ուսումնասիրություն։')
    triggers=[{'name':r['name'],'parent':r.get('parent_object'),'disabled':bool(r['is_disabled'])} for r in snapshot.get('triggers',[])]
    if triggers:warnings.append('Trigger-ների վարքը չի ստուգվել. transaction-ից դուրս կողմնակի ազդեցությունները նույնպես անհայտ են։')
    warnings.append('View-երի տեքստի համընկնումը դրանց իրական վարքի թեստ չէ։')
    return {'structural_status':'incomplete' if not full else 'mismatch' if errors else 'matched',
            'checked_properties':checked,'errors':errors,'warnings':warnings,'view_definition_comparison':definitions,
            'view_metadata_not_asserted':contract['view_metadata_not_asserted'],
            'triggers':triggers,'runtime_behavior':'NOT_TESTED','backup_correspondence':'UNCONFIRMED',
            'source_fingerprints':contract['source'],'database':snapshot.get('database',[{}])[0].get('database_name')}

def inspect_database(engine):
    if engine.dialect.name!='mssql':raise ValueError('Այս գործիքը նախատեսված է միայն Microsoft SQL Server-ի համար։')
    with engine.connect() as db:return collect_metadata(db)

def main(argv=None):
    parser=argparse.ArgumentParser(description='Read-only SQL Server structural checks')
    parser.add_argument('--metadata',type=Path,help='Compare an existing metadata export without connecting')
    parser.add_argument('--output',type=Path,default=Path('exports/schema_verification.json'))
    args=parser.parse_args(argv)
    try:
        snapshot=json.loads(args.metadata.read_text(encoding='utf-8-sig')) if args.metadata else inspect_database(get_engine())
        report=compare_metadata(snapshot,json.loads(CONTRACT_PATH.read_text()))
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('Կառուցվածքային արդյունք՝ '+report['structural_status'])
        for error in report['errors']:print(error)
        for warning in report['warnings']:print(warning)
        print('Բազան չի փոփոխվել։ Backup-ի հետ համապատասխանությունը դեռ հաստատված չէ։')
        print('Հաշվետվություն՝ '+str(args.output))
        return 1 if report['errors'] else 2 if any(v!='text_match' for v in report['view_definition_comparison'].values()) or any(not t['disabled'] for t in report['triggers']) else 0
    except Exception as exc:
        print('Ստուգումը չի ավարտվել։ Ստուգեք միացումը, metadata-ն և VIEW DEFINITION իրավունքը։')
        print('Սխալի տեսակ՝ '+type(exc).__name__)
        return 1
if __name__=='__main__':raise SystemExit(main())
