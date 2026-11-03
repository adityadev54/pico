"""Read only selected, granted text documents. No OCR, URLs, or hidden files."""
from pathlib import Path
import zipfile,xml.etree.ElementTree as ET


def scoped(root, relative):
    root=Path(root).resolve();p=(root/relative).resolve()
    if not p.is_relative_to(root) or p==root or any(part.startswith('.') for part in Path(relative).parts):
        raise ValueError('Choose a visible file inside the approved workspace.')
    if p.suffix.lower() in ('.pem','.key','.p12','.pfx'):
        raise ValueError('Credential files cannot be teaching inputs.')
    return p


def read_document(path):
    p=Path(path)
    if not p.is_file() or p.stat().st_size>2_000_000:raise ValueError('Choose a document below 2 MB.')
    kind=p.suffix.lower()
    if kind in ('.txt','.md','.csv'):text=p.read_text(encoding='utf-8')
    elif kind=='.docx':
        with zipfile.ZipFile(p) as z:
            info=z.getinfo('word/document.xml')
            if info.file_size>2_000_000:raise ValueError('The Word document is too large.')
            xml=ET.fromstring(z.read(info))
            text='\n'.join(''.join(n.itertext()) for n in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'))
    elif kind=='.pdf':
        from pypdf import PdfReader
        doc=PdfReader(p)
        if len(doc.pages)>20:raise ValueError('Choose at most 20 PDF pages.')
        text='\n'.join(page.extract_text() or '' for page in doc.pages)
    else:raise ValueError('Use text, Markdown, CSV, DOCX, or a text-based PDF. Photos are not read by this workflow.')
    if not text.strip():raise ValueError('No readable text. A scanned PDF needs OCR before teaching.')
    if len(text)>6000:raise ValueError('Choose shorter notes (6,000 characters maximum per document); nothing was silently truncated.')
    return text
