import copy,json
import pytest
from tools.verify_schema import compare_metadata,CONTRACT_PATH

@pytest.fixture
def contract():return json.loads(CONTRACT_PATH.read_text())

@pytest.fixture
def metadata_snapshot(contract):
    data={'database':[{'database_name':'TestOnly','can_view_definition':1}], 'objects':[],'columns':[],'indexes':[],'foreign_keys':[],'modules':[],'triggers':[]}
    for name,spec in [*contract['tables'].items(),*((n,{'columns':c}) for n,c in contract['view_columns'].items())]:
        data['objects'].append({'schema_name':'dbo','name':name,'type_desc':'USER_TABLE' if name in contract['tables'] else 'VIEW'})
        for col,props in spec['columns'].items():data['columns'].append({'schema_name':'dbo','object_name':name,'name':col,**props})
    for table,spec in contract['tables'].items():
        for j,key in enumerate([{'columns':spec['primary_key'],'primary':True,'filter':None}]+spec['unique_keys']):
            for ordinal,col in enumerate(key['columns'],1):
                data['indexes'].append({'schema_name':'dbo','table_name':table,'name':f'index{j}','is_unique':True,'is_primary_key':key.get('primary',False),'is_disabled':False,'filter_definition':key['filter'],'column_name':col,'key_ordinal':ordinal,'is_included_column':False})
        for j,key in enumerate(spec['foreign_keys']):
            for ordinal,(src,dst) in enumerate(zip(key['source_columns'],key['target_columns']),1):
                data['foreign_keys'].append({'source_schema':'dbo','source_table':table,'name':f'fk{j}','source_column':src,'target_schema':key['target_schema'],'target_table':key['target_table'],'target_column':dst,'constraint_column_id':ordinal,'is_disabled':False,'is_not_trusted':False})
    for name,definition in contract['view_definitions'].items():data['modules'].append({'schema_name':'dbo','name':name,'definition':definition})
    return data

def test_complete_metadata_matches_but_not_backup_or_runtime(metadata_snapshot,contract):
    report=compare_metadata(metadata_snapshot,contract)
    assert report['structural_status']=='matched' and report['errors']==[]
    assert report['checked_properties']>400
    assert report['backup_correspondence']=='UNCONFIRMED'
    assert report['runtime_behavior']=='NOT_TESTED'

@pytest.mark.parametrize('property,value',[('type_name','varchar'),('max_length',150),('is_nullable',True),('is_identity',True)])
def test_wrong_type_byte_length_nullability_identity(metadata_snapshot,contract,property,value):
    column=next(c for c in metadata_snapshot['columns']if c['object_name']=='Lecturers'and c['name']=='FirstName')
    # FirstName is nvarchar(150) NOT NULL, not identity; max_length must be 300 bytes.
    column[property]=value
    assert compare_metadata(metadata_snapshot,contract)['structural_status']=='mismatch'

def test_missing_primary_unique_and_disabled_fk(metadata_snapshot,contract):
    metadata_snapshot['indexes']=[i for i in metadata_snapshot['indexes']if i['table_name']not in ['Lecturers','StudentCourses']]
    next(r for r in metadata_snapshot['foreign_keys']if r['source_table']=='Courses')['is_not_trusted']=True
    report=compare_metadata(metadata_snapshot,contract)
    assert any('հիմնական բանալին'in e for e in report['errors'])
    assert any('UNIQUE'in e for e in report['errors'])
    assert any('FK'in e for e in report['errors'])

def test_incomplete_permissions_is_not_success(metadata_snapshot,contract):
    metadata_snapshot['database'][0]['can_view_definition']=0
    assert compare_metadata(metadata_snapshot,contract)['structural_status']=='incomplete'

def test_unknown_view_and_trigger_behavior_explicit(metadata_snapshot,contract):
    metadata_snapshot['modules'][0]['definition']='CREATE VIEW changed AS SELECT 1'
    metadata_snapshot['triggers']=[{'name':'unknown_trigger','parent_object':'Ratings','is_disabled':False}]
    report=compare_metadata(metadata_snapshot,contract)
    assert 'text_differs'in report['view_definition_comparison'].values()
    assert report['runtime_behavior']=='NOT_TESTED'
    assert report['triggers'][0]['name']=='unknown_trigger'
    assert report['view_metadata_not_asserted']

def test_numeric_synonym_and_multicolumn_order(metadata_snapshot,contract):
    for c in metadata_snapshot['columns']:
        if c['type_name']=='decimal':c['type_name']='numeric'
    assert compare_metadata(metadata_snapshot,contract)['structural_status']=='matched'
    rows=[i for i in metadata_snapshot['indexes']if i['table_name']=='StudentCourses'and not i['is_primary_key']]
    for r in rows:r['key_ordinal']=3-r['key_ordinal']
    assert compare_metadata(metadata_snapshot,contract)['structural_status']=='mismatch'

def test_new_required_column_is_not_silently_accepted(metadata_snapshot,contract):
    metadata_snapshot['columns'].append({'schema_name':'dbo','object_name':'Lecturers','name':'UnexpectedRequired','type_name':'int','is_nullable':False,'is_identity':False,'is_computed':False,'default_definition':None})
    report=compare_metadata(metadata_snapshot,contract)
    assert report['structural_status']=='mismatch'
    assert any('UnexpectedRequired'in e for e in report['errors'])
