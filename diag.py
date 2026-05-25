import zipfile, re

docx_path = 'output/test_output.docx'
with zipfile.ZipFile(docx_path, 'r') as z:
    with z.open('word/document.xml') as f:
        content = f.read().decode('utf-8')

    print('=== Text direction check ===')
    for pattern in ['textDirection', 'writingMode', 'tbRl', 'vertical', 'textLayout']:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        if matches:
            print(f'  FOUND "{pattern}": {len(matches)} matches')
        else:
            print(f'  No "{pattern}"')

    print()
    print('=== Paragraphs ===')
    paras = re.findall(r'<w:p[ >].*?</w:p>', content, re.DOTALL)
    print(f'Total paragraphs: {len(paras)}')
    for i, p in enumerate(paras[:6]):
        text_content = re.sub(r'<[^>]+>', '', p).strip()
        runs = re.findall(r'<w:t[^>]*>([^<]+)</w:t>', p)
        print(f'  Para {i}: [{text_content[:50]}] runs={runs}')

    print()
    print('=== Body properties (w:bodyPr) ===')
    body_match = re.search(r'<w:bodyPr[^>]*/>', content)
    if body_match:
        print(body_match.group(0))
    else:
        print('No w:bodyPr found')

    print()
    print('=== SectPr full ===')
    sect = re.search(r'<w:sectPr[^>]*>.*?</w:sectPr>', content, re.DOTALL)
    if sect:
        print(sect.group(0)[:1500])

    print()
    print('=== Settings ===')
    with z.open('word/settings.xml') as f:
        settings = f.read().decode('utf-8')
    print(settings[:2000])
