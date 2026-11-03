"""Pure, shared output validation; no networking or credentials."""
from pathlib import Path
from urllib.parse import quote

def validate_pack(value,sources):
    if isinstance(value,dict) and "sections" in value:return validate_sections(value,sources)
    if not isinstance(value,dict) or set(value)!={'title','ideas','questions'}:raise ValueError('Muse returned an incomplete study pack. No automatic retry.')
    if not isinstance(value['title'],str) or not value['title'].strip() or len(value['title'])>120:raise ValueError('Invalid title.')
    texts={r['id']:r['text'] for r in sources}
    for kind,keys in [('ideas',{'text','source','quote'}),('questions',{'question','answer','source','quote'})]:
        if not isinstance(value[kind],list) or len(value[kind])!=2:raise ValueError('The study pack needs two ideas and two practice questions.')
        for item in value[kind]:
            if not isinstance(item,dict) or set(item)!=keys:raise ValueError('Incomplete study material.')
            if any(not isinstance(v,str) or not v.strip() or len(v)>500 for v in item.values()):raise ValueError('Invalid study material.')
            if item['source'] not in texts or len(item['quote'])>100 or item['quote'] not in texts[item['source']]:raise ValueError('A study-pack citation was not found in the selected notes.')
    return value

def render_pack(value,rows,output,root):
    import os
    links={r['id']:quote(os.path.relpath(Path(root)/r['name'],Path(output).parent)) for r in rows}
    if 'sections' in value:
        parts=['# '+value['title'],'']
        for section in value['sections']:
            parts+=['## '+section['heading'],'']
            for item in section['items']:parts+=['- '+item['text']+f" ([{item['source']}]({links[item['source']]}))",'  > '+item['quote'],'']
        return '\n'.join(parts)+'\n'
    parts=['# '+value['title'],'','## Key ideas','']
    for item in value['ideas']:parts+=['- '+item['text']+f" ([{item['source']}]({links[item['source']]}))",'  > '+item['quote'],'']
    parts+=['## Practice questions','']
    for i,item in enumerate(value['questions'],1):parts += [f"{i}. {item['question']}",f"   Answer: {item['answer']} ([{item['source']}]({links[item['source']]}))",'   > '+item['quote'],'']
    parts+=['---','Generated from the selected notes. Citations were checked against their exact text; review interpretations before relying on them.']
    return '\n'.join(parts)+'\n'


def validate_sections(value,sources):
    if set(value)!={'title','sections'} or not isinstance(value['title'],str) or not 1<=len(value['title'])<=120:raise ValueError('Invalid prepared output.')
    sections=value['sections'];texts={r['id']:r['text'] for r in sources}
    if not isinstance(sections,list) or not 1<=len(sections)<=4:raise ValueError('Use one to four output sections.')
    total=0
    for section in sections:
        if not isinstance(section,dict) or set(section)!={'heading','items'} or not isinstance(section['heading'],str) or not 1<=len(section['heading'])<=100:raise ValueError('Invalid output section.')
        items=section['items']
        if not isinstance(items,list) or not 1<=len(items)<=6:raise ValueError('Invalid section items.')
        total+=len(items)
        for item in items:
            if not isinstance(item,dict) or set(item)!={'text','source','quote'} or any(not isinstance(v,str) or not v.strip() for v in item.values()):raise ValueError('Incomplete source-backed output.')
            if len(item['text'])>700 or item['source'] not in texts or not 1<=len(item['quote'])<=100 or item['quote'] not in texts[item['source']]:raise ValueError('An output citation was not found in the selected files.')
    if total>10:raise ValueError('Keep this bounded output below eleven items.')
    return value
