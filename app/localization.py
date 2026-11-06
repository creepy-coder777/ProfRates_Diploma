"""Presentation-only English names. No database values are rewritten.

Personal names use transliteration; department names use explicit translations.
Extend DEPARTMENTS for newly added departments rather than guessing translations.
"""
DEPARTMENTS = {
    'Ինֆորմատիկա և հաշվողական տեխնիկա': 'Informatics and Computer Engineering',
    'Տեղեկատվական տեխնոլոգիաներ և ավտոմատացում': 'Information Technologies and Automation',
    'Կապի համակարգեր': 'Communication Systems',
    'Ռադիոսարքավորումներ': 'Radio Equipment',
    'Էլեկտրոնիկա, կենսաբժշկական և չափիչ համակարգեր': 'Electronics, Biomedical and Measurement Systems',
    'Էլեկտրական մեքենաներ և ապարատներ': 'Electrical Machines and Apparatus',
    'Էլեկտրատեխնիկա և էլեկտրաբանեցում': 'Electrical Engineering and Electric Drives',
    'Էլեկտրամատակարարում': 'Power Supply',
    'Ատոմային և ջերմաէներգետիկա': 'Nuclear and Thermal Power Engineering',
    'Ճարտարագիտական գրաֆիկա': 'Engineering Graphics',
    'Դիզայն և արվեստ': 'Design and Art',
    'Փոխադրումների կազմակերպում': 'Transport Organization',
    'Մեքենաշինության տեխնոլոգիաներ և ավտոմատացում': 'Mechanical Engineering Technologies and Automation',
    'Հանքագործություն': 'Mining',
    'Մետաղագործություն': 'Metallurgy',
    'Քիմիա-կենսա- և բնապահպանական տեխնոլոգիաներ': 'Chemical, Biological and Environmental Technologies',
    'Ընդհանուր մաթեմատիկական կրթություն': 'General Mathematics Education',
    'Ֆիզիկա': 'Physics',
    'Մասնագիտացված մաթեմատիկական կրթություն': 'Specialized Mathematics Education',
    'Համակարգչային համակարգեր և ցանցեր': 'Computer Systems and Networks',
    'Տեղեկատվական անվտանգություն և ծրագրային ապահովում': 'Information Security and Software Engineering',
}
LETTERS = dict(zip('աբգդեզէըթժիլխծկհձղճմյնշոչպջռսվտրցւփքօֆ',
    ['a','b','g','d','e','z','e','y','t','zh','i','l','kh','ts','k','h','dz','gh','ch','m','y','n','sh','o','ch','p','j','r','s','v','t','r','ts','u','p','k','o','f']))


def transliterate(value):
    if not value:
        return value
    result = []
    i = 0
    while i < len(value):
        char = value[i]
        if value[i:i+2].lower() == 'ու':
            piece = 'u'; i += 2
        elif char == 'և':
            piece = 'ev'; i += 1
        else:
            piece = LETTERS.get(char.lower(), char); i += 1
        result.append(piece.capitalize() if char.isupper() else piece)
    return ''.join(result)


def department(value):
    # Unknown terms remain authoritative Armenian rather than fabricated English.
    return DEPARTMENTS.get(value, value)


PATRONYMIC_BASES = {name+'ի':name for name in (
    'Արամ','Ռուբեն','Հրանտ','Արմեն','Ալբերտ','Սուրեն','Կարեն','Հայկ','Ռաֆիկ',
    'Վաղարշակ','Կամո','Ռոբերտ','Արթուր','Արտուր','Ղևոնդ','Վարդան','Ժիրայր',
    'Սամվել','Հակոբ','Վաչագան','Գագիկ','Անդրանիկ','Լևոն','Գուրգեն','Միքայել',
    'Էդուարդ','Ռաֆայել','Արա')}
PATRONYMIC_BASES.update({'Դավթի':'Դավիթ','Արայի':'Արա','Կամոյի':'Կամո'})

# A portrait belongs to the full person name, across course-specific lecturer IDs.
DEMO_PORTRAITS = {
    ('Արամ','Ռուբենի','Ղազարյան'):'lecturer-01.jpg',
    ('Մարինե','Սուրենի','Հովհաննիսյան'):'lecturer-02.jpg',
    ('Վահե','Հրանտի','Մկրտչյան'):'lecturer-03.jpg',
    ('Անի','Արմենի','Սիմոնյան'):'lecturer-04.jpg',
    ('Գագիկ','Ալբերտի','Պետրոսյան'):'lecturer-05.jpg',
    ('Նարինե','Կարենի','Ավետիսյան'):'lecturer-06.jpg',
    ('Դավիթ','Հայկի','Ասատրյան'):'lecturer-07.jpg',
    ('Տաթևիկ','Ռաֆիկի','Գրիգորյան'):'lecturer-08.jpg',
    ('Արտուր','Վաղարշակի','Բաղդասարյան'):'lecturer-09.jpg',
    ('Սոնա','Կամոյի','Կարապետյան'):'lecturer-10.jpg',
}


def portrait_identity(parts):
    import unicodedata
    return tuple(unicodedata.normalize('NFC',' '.join((value or '').split())).casefold()
                 for value in parts)


_PORTRAITS_BY_NAME = {portrait_identity(identity):filename
                      for identity,filename in DEMO_PORTRAITS.items()}


def english_patronymic(value):
    if not value:
        return value
    value=value.strip()
    bases={**PATRONYMIC_BASES,
           **{transliterate(key):transliterate(base) for key,base in PATRONYMIC_BASES.items()}}
    # Unknown names are transliterated intact; never truncate arbitrary final 'i'.
    return transliterate(bases.get(value,value))


def lecturer(item, lang):
    item = dict(item)
    identity=portrait_identity(item.get(key) for key in ('FirstName','MiddleName','LastName'))
    demo = _PORTRAITS_BY_NAME.get(identity)
    if not item.get('PhotoUrl') and demo:
        item['PhotoUrl'] = '/frontend/assets/'+demo
        item['PhotoIsDemo'] = True
    if lang != 'en':
        return item
    for key in ('FirstName', 'MiddleName', 'LastName'):
        if key in item:
            item[key] = english_patronymic(item[key]) if key=='MiddleName' else transliterate(item[key])
    item['Chairs'] = [department(value) for value in item.get('Chairs', [])]
    return item


def lecturer_page(result, lang):
    return {**result, 'items': [lecturer(item, lang) for item in result['items']]}



def person_display(item, lang):
    """Keep editable official fields unchanged; add a localized display name."""
    result = dict(item)
    names = [result.get(key) for key in ('FirstName', 'LastName')]
    if lang == 'en':
        labels = {'Ադմինիստրատոր':'Administrator', 'Գլխավոր':'Main'}
        names = [labels.get(value, transliterate(value)) for value in names]
    result['DisplayName'] = ' '.join(value for value in names if value)
    return result
