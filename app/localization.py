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


def lecturer(item, lang):
    if lang != 'en':
        return item
    item = dict(item)
    for key in ('FirstName', 'MiddleName', 'LastName'):
        if key in item:
            item[key] = transliterate(item[key])
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
