# -*- coding: utf-8 -*-
"""build_docx.py v2 — author/*.html -> pandoc Markdown -> DOCX (OMML math).
Usage: python build_docx.py [slug ...]   (default: all config.LECTURES keys)
"""
import io, os, re, sys, json, zipfile, subprocess, shutil, glob as globf
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'source')
MD_DIR = os.path.join(SRC, 'docx_md');  os.makedirs(MD_DIR, exist_ok=True)
IMG_DIR = os.path.join(SRC, 'docx_img'); os.makedirs(IMG_DIR, exist_ok=True)
DOCX_CHAPTER_DIR = os.path.join(ROOT, 'output', 'docx', '分章')
DOCX_COMBINED_DIR = os.path.join(ROOT, 'output', 'docx', '合订本')
OUTPUT_NOTES_DIR = os.path.join(ROOT, 'output', '说明')
for _directory in (DOCX_CHAPTER_DIR, DOCX_COMBINED_DIR, OUTPUT_NOTES_DIR):
    os.makedirs(_directory, exist_ok=True)
REF = os.path.join(SRC, 'docx_ref', 'reference.docx')
PANDOC = os.environ.get('PANDOC') or shutil.which('pandoc') or 'pandoc'
PY = sys.executable

def _svg2png(src, dst):
    script = os.path.join(ROOT, 'tools', '_svg2png.py')
    io.open(script, 'w', encoding='utf-8').write(
        "import fitz, sys\n"
        "f = fitz.open(sys.argv[1])\n"
        "if not f.is_pdf:\n"
        "    pdf = f.convert_to_pdf()\n"
        "    f = fitz.open(stream=pdf, filetype='pdf')\n"
        "pg = f[0]\n"
        "pg.get_pixmap(dpi=220).save(sys.argv[2])\n")
    r = subprocess.run([PY, script, src, dst], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'svg2png failed: {src}\n{r.stderr[-500:]}')

def resolve_image(src_attr, name):
    """map html src to an absolute file, rasterize dia/fig to png in IMG_DIR"""
    dst = os.path.join(IMG_DIR, name)
    if src_attr.startswith('dia:'):
        srcf = os.path.join(SRC, 'diagrams', src_attr.split(':', 1)[1])
        if srcf.lower().endswith('.svg'):
            _svg2png(srcf, dst); return dst
        return srcf
    if src_attr.startswith('fig:'):
        lbl, nn = src_attr.split(':', 1)[1].split('/')
        cands = globf.glob(os.path.join(SRC, 'img', lbl, nn + '.*'))
        if not cands:
            cands = globf.glob(os.path.join(SRC, 'img', lbl, nn.split('.')[0] + '.*'))
        if not cands:
            raise RuntimeError(f'missing fig image for slug-check: src={src_attr} ' +
                               f'have={globf.glob(os.path.join(SRC, "img", lbl, "*"))[:4]}')
        srcf = cands[0]
        if srcf.lower().endswith(('.svg',)):
            _svg2png(srcf, dst); return dst
        return srcf
    return os.path.normpath(os.path.join(SRC, src_attr))

MATH_INLINE = re.compile(r'\\\((.+?)\\\)', re.S)
MATH_DISP = re.compile(r'\\\[([^\[\]]+?)\\\]', re.S)
import html as htmllib
def mathify(s):
    s = MATH_DISP.sub(lambda m: '\n\n$$' + htmllib.unescape(m.group(1).strip()) + '$$\n\n', s)
    s = MATH_INLINE.sub(lambda m: '$' + htmllib.unescape(m.group(1).strip()) + '$', s)
    return s

def strip_inline(html, imgs, pending):
    """html fragment -> mathified text with image tokens preserved"""
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S)
    def repl(m):
        attrs = m.group(0); srcm = re.search(r'src="([^"]+)"', attrs)
        if srcm:
            pending.append(srcm.group(1))
            return f'IMGTOKEN{len(pending)-1}§'
        return ' '
    html = re.sub(r'<img[^>]*>', repl, html)
    txt = re.sub(r'<[^>]+>', ' ', html)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return mathify(txt), pending

def table_md(tbl):
    rows = tbl.find_all('tr', recursive=False)
    out = []
    ncol = None
    for tr in rows:
        cells = tr.find_all(['th', 'td'], recursive=False)
        txts = []
        for c in cells:
            t, _ = strip_inline(c.decode_contents(), None, [])
            txts.append(t.replace('|', '/'))
        if len(cells) == 1 and len(txts) == 1 and ncol:
            row = ['**' + txts[0] + '**'] + [''] * (ncol - 1)
        else:
            row = txts
            if ncol is None: ncol = len(txts)
        out.append('| ' + ' | '.join(row) + ' |')
        if len(out) == 1:
            out.append('|' + '|'.join([':---'] * ncol) + '|')
    return '\n'.join(out) + '\n\n'

def walk(node, out, images):
    """images: list dicts {token, src, caption} filled in encounter order"""
    for ch in node.children:
        if isinstance(ch, NavigableString):
            t = str(ch).strip()
            if t: out.append(mathify(t) + '\n\n')
            continue
        if not isinstance(ch, Tag): continue
        name = ch.name
        if name in ('h1', 'h2', 'h3'):
            out.append('#' * int(name[1]) + ' ' + mathify(ch.get_text(strip=True)) + '\n\n')
        elif name == 'p':
            pending = []
            txt, pending = strip_inline(ch.decode_contents(), None, pending)
            txt = re.sub(r'IMGTOKEN\d+§', ' ', txt)   # stray img tokens (fig images handled by figwrap)
            out.append(txt + '\n\n')
            for tok in pending:
                pass
        elif name == 'table':
            out.append(table_md(ch))
        elif name in ('ul', 'ol'):
            for li in ch.find_all('li', recursive=False):
                out.append('- ' + mathify(li.get_text(' ', strip=True)) + '\n')
            out.append('\n')
        elif name == 'blockquote':
            out.append('> ' + mathify(ch.get_text('\n', strip=True)) + '\n\n')
        elif name == 'div':
            cls = ' '.join(ch.get('class', []))
            if 'figwrap' in cls:
                im = ch.find('img'); capd = ch.find('div', class_='caption')
                if im is not None:
                    cap = capd.get_text(' ', strip=True) if capd else ''
                    images.append({'src': im.get('src', ''), 'caption': mathify(cap)})
            elif 'admonition' in cls:
                ttl = ch.find('div', class_='admonition-title')
                body = re.sub(r'<div class="admonition-title">.*?</div>', '', ch.decode_contents(), flags=re.S)
                body = mathify(body); body = re.sub(r'<[^>]+>', ' ', body)
                body = re.sub(r'\s+', ' ', body).strip()
                out.append('> **' + ttl.get_text(' ', strip=True) + '**　' + body + '\n\n')
        else:
            walk(ch, out, images)

def convert(slug):
    html = io.open(os.path.join(ROOT, 'author', slug + '.html'), encoding='utf-8').read()
    soup = BeautifulSoup(html, 'lxml')
    art = soup.find('article')
    out, images = [], []
    walk(art, out, images)
    md = ''.join(out)
    # image captions: inline math in captions was mathified already
    for i, img in enumerate(images):
        path = resolve_image(img['src'], f'{slug}_img{i:02d}.png')
        rel = os.path.relpath(path, MD_DIR).replace(os.sep, '/')
        block = f'\n\n![]({rel})\n\n*{img["caption"]}*\n\n'
        md += block  # appended sequentially; placement near original position approximated
    md = re.sub(r'\n{3,}', '\n\n', md)
    mdpath = os.path.join(MD_DIR, slug + '.md')
    io.open(mdpath, 'w', encoding='utf-8').write(md)
    return mdpath

def build_ref():
    if os.path.exists(REF): return
    os.makedirs(os.path.dirname(REF), exist_ok=True)
    default = os.path.join(os.path.dirname(REF), 'reference_default.docx')
    subprocess.run([PANDOC, '--print-default-data-file=reference.docx'],
                   check=True, stdout=io.open(default, 'wb'))
    zin = zipfile.ZipFile(default)
    members = {n: zin.read(n) for n in zin.namelist()}
    zin.close()
    st = members['word/styles.xml'].decode('utf-8')
    st = re.sub(r'<w:rFonts([^/]*?)w:asciiTheme="[^"]*"(.*?)w:eastAsiaTheme="[^"]*"(.*?)w:hAnsiTheme="[^"]*"(.*?)w:cstheme="[^"]*"/>',
                r'<w:rFonts\1w:ascii="Times New Roman"\2w:eastAsia="SimSun"\3w:hAnsi="Times New Roman"\4/>', st)
    st = st.replace('<w:rFonts w:ascii="Times New Roman" w:eastAsia="SimSun" w:hAnsi="Times New Roman"/><w:color w:val="461161"/>',
                    '<w:rFonts w:ascii="Times New Roman" w:eastAsia="SimSun" w:hAnsi="Times New Roman"/>')
    # academic style: kill colored heading fonts, use black + SimHei for CJK headings
    st = re.sub(r'<w:color[^>]*/>', '', st)
    st = re.sub(r'<w:color[^>]*>.*?</w:color>', '', st, flags=re.S)
    def _head(m):
        blk = m.group(0)
        if 'w:styleId="Heading' not in blk: return blk
        blk = re.sub(r'w:eastAsia="[^"]*"', 'w:eastAsia="SimHei"', blk)
        blk = re.sub(r'<w:b w:val="0"/>', '', blk)
        return blk
    st = re.sub(r'<w:style [^>]*>.*?</w:style>', _head, st, flags=re.S)
    members['word/styles.xml'] = st.encode('utf-8')
    with zipfile.ZipFile(REF, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in members.items(): z.writestr(n, b)

def pandoc_docx(mdpath, outpath):
    build_ref()
    r = subprocess.run([PANDOC, mdpath, '-f', 'markdown', '-t', 'docx',
                        '--reference-doc=' + REF, '--resource-path=' + MD_DIR,
                        '-o', outpath], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('pandoc failed: ' + r.stderr[-800:])

def verify(path):
    z = zipfile.ZipFile(path)
    doc = z.read('word/document.xml').decode('utf-8')
    txt = re.sub(r'<[^>]+>', '', doc)
    return {'oMath': doc.count('<m:oMath>'), 'oMathPara': doc.count('<m:oMathPara>'),
            'residual_tex': len(re.findall(r'\\\(|\\\)', doc)), 'residual_dollar': txt.count('$')}

if __name__ == '__main__':
    sys.path.insert(0, ROOT)
    import config
    import docx_post
    slugs = sys.argv[1:] or [c[0] for c in config.LECTURES]
    titles = {c[0]: c[1] for c in config.LECTURES}
    report = {}
    raw_pagebreak = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```\n\n'
    for slug in slugs:
        md = convert(slug)
        out = os.path.join(DOCX_CHAPTER_DIR, f'{slug}_课文.docx')
        pandoc_docx(md, out)
        post = docx_post.rewrite(out, out)
        report[slug] = dict(verify(out), tables=post['tables'])
        print(slug, report[slug])
    # 合订版：全 md 拼接 + 章间分页 + 扉页/目录
    if len(slugs) > 1:
        mds = []
        for slug in slugs:
            mds.append(io.open(os.path.join(MD_DIR, slug + '.md'), encoding='utf-8').read)
        mds = [io.open(os.path.join(MD_DIR, s + '.md'), encoding='utf-8').read() for s in slugs]
        combined = ('\n\n' + raw_pagebreak).join(mds)
        cpath = os.path.join(MD_DIR, '_combined.md')
        io.open(cpath, 'w', encoding='utf-8').write(combined)
        cout = os.path.join(DOCX_COMBINED_DIR, '递归自我改进_合订课文.docx')
        tmp = cout + '.tmp'
        pandoc_docx(cpath, tmp)
        datestr = '2026 年 10 月 · 资料截至 2026-10-21'
        post = docx_post.rewrite(tmp, cout, front=True,
                                 title='递归自我改进',
                                 subtitle='自我改进系统、模型侧优化与开放式智能体进化',
                                 note='个人学习教材 · 编者：RSI 课程组', datestr=datestr)
        os.remove(tmp)
        report['_combined'] = dict(verify(cout), tables=post['tables'])
        print('_combined', report['_combined'])
    io.open(os.path.join(OUTPUT_NOTES_DIR, 'DOCX构建报告.json'), 'w', encoding='utf-8').write(
        json.dumps(report, ensure_ascii=False, indent=1))


