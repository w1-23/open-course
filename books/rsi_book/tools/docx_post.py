# -*- coding: utf-8 -*-
"""docx_post.py 鈥?post-process pandoc DOCX.
1) three-line (booktabs) tables with proportional column widths + compact spacing
2) math runs normalized to body font size, bold stripped
3) front matter (鎵夐〉 + TOC field) as its own section; body page numbers restart at 1
4) settings.xml updateFields=true
Usage: python docx_post.py <docx> [--front] [--title ..] [--subtitle ..] [--date ..]
"""
import io, os, re, sys, zipfile, copy
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M = 'http://schemas.openxmlformats.org/officeDocument/2006/math'
nsw = {'w': W, 'm': M}
SEMI = '{%s}%%s' % W  # helper unused
def w(t):
    if t.lstrip().startswith('<'):
        return t  # raw xml fragment passthrough
    return '{%s}%s' % (W, t)

_NS = 'xmlns:w="%s"' % W
_FS = etree.fromstring
def pxml(s):
    s = s.strip()
    if 'xmlns:' not in s.split('>', 1)[0]:
        s = '<rt %s>%s</rt>' % (_NS, s)
    return _FS(s)[0]
def mw(t): return '{%s}%s' % (M, t)

BODY_SZ = '24'      # 12pt body (灏忓洓)
TABLE_SZ = '18'     # 9pt in tables (灏忎簲)
MATH_SZ = '20'      # 10pt math, slightly smaller than 12pt body

def q(fmt): return fmt.format(W=W, M=M)

def _el(t):
    return etree.SubElement if False else etree.Element(t)

def _borders_none():
    mk = lambda b: None
    out = []
    for b in ('left', 'right', 'insideV', 'insideH'):
        e = pxml(w('<w:{b} w:val="none" w:sz="0" w:space="0"/>'.replace('{b}', b)))
        out.append(e)
    def topbot(sz):
        e1 = pxml(w('<w:top w:val="single" w:sz="%d" w:space="0" w:color="auto"/>' % sz))
        e2 = pxml(w('<w:bottom w:val="single" w:sz="%d" w:space="0" w:color="auto"/>' % sz))
        return e1, e2
    return out, topbot

def three_line(doc):
    """booktabs-ify every table"""
    n = 0
    for tbl in doc.iter(w('tbl')):
        n += 1
        # --- tblPr: explicit three-line borders, compact cell margins ---
        tblPr = tbl.find(w('tblPr'))
        if tblPr is None:
            tblPr = etree.SubElement(tbl, w('tblPr'))
        # rebuild tblBorders
        old = tblPr.find(w('tblBorders'))
        if old is not None: tblPr.remove(old)
        bs = etree.SubElement(tblPr, w('tblBorders'))
        for e in _borders_none()[0]: bs.append(e)
        for name in ('top', 'bottom'):
            bs.append(pxml(w('<w:%s w:val="single" w:sz="12" w:space="0" w:color="auto"/>' % name)))
        # order inside tblBorders: top,left,bottom,right,insideH,insideV 鈥?Word is lenient but be safe
        order = [ 'top','left','bottom','right','insideH','insideV']
        g = {c.tag: c for c in bs}
        for c in list(bs): bs.remove(c)
        for nm in order:
            t = '{%s}%s' % (W, nm)
            if t in g: bs.append(g[t])
        om = tblPr.find(w('tblCellMar'))
        if om is not None: tblPr.remove(om)
        cm = pxml(w(
            '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="85" w:type="dxa"/>'
            '<w:bottom w:w="20" w:type="dxa"/><w:right w:w="85" w:type="dxa"/></w:tblCellMar>'))
        tblPr.append(cm)
        # keep table full width & fixed layout
        lay = tblPr.find(w('tblLayout'))
        if lay is None: lay = etree.SubElement(tblPr, w('tblLayout'))
        lay.set(w('type'), 'fixed')
        # --- column weights by content length ---
        rows = tbl.findall(w('tr'))
        grid = tbl.find(w('tblGrid'))
        ncol = len(rows[0].findall(w('tc'))) if rows else 0
        weights = [0.0] * ncol
        for tr in rows:
            tcs = tr.findall(w('tc'))
            if len(tcs) != ncol: continue
            for j, tc in enumerate(tcs):
                txt = ''.join(tc.itertext())
                weights[j] = max(weights[j], min(len(txt), 400))
        weights = [max(10.0, min(x, 30.0)) for x in weights]
        # usable width from sectPr
        usable = 9000
        for sect in doc.iter(w('sectPr')):
            pg = sect.find(w('pgSz')); mg = sect.find(w('pgMar'))
            if pg is not None and mg is not None:
                usable = int(pg.get(w('w'))) - int(mg.get(w('left') if mg.get(w('left')) else 'left')) - int(mg.get(w('right'))) if False else usable
        # just compute from any sect with pgSz/pgMar
        for sect in doc.iter(w('sectPr')):
            pg = sect.find(w('pgSz')); mg = sect.find(w('pgMar'))
            if pg is not None and mg is not None:
                usable = int(pg.get(w('w'))) - int(mg.get(w('left'))) - int(mg.get(w('right')))
                break
        tot = sum(weights)
        widths = [max(int(usable * x / tot), 360) for x in weights]
        # renormalize rounding to exact usable
        diff = usable - sum(widths)
        widths[-1] += diff
        if grid is not None:
            for gc in list(grid): grid.remove(gc)
            for wd in widths:
                gc = etree.SubElement(grid, w('gridCol')); gc.set(w('w'), str(wd))
        # per-row cell widths + styling
        for i, tr in enumerate(rows):
            tcs = tr.findall(w('tc'))
            if len(tcs) != ncol: continue
            if i == 0:
                # header repeat
                trPr = tr.find(w('trPr'))
                if trPr is None: trPr = etree.SubElement(tr, w('trPr'))
                if trPr.find(w('tblHeader')) is None:
                    etree.SubElement(trPr, w('tblHeader'))
            for j, tc in enumerate(tcs):
                tcPr = tc.find(w('tcPr'))
                if tcPr is None: tcPr = etree.SubElement(tc, w('tcPr'))
                for tag in ('tcW', 'tcBorders', 'shd', 'vAlign'):
                    e = tcPr.find(w(tag))
                    if e is not None: tcPr.remove(e)
                tcW = etree.Element(w('tcW')); tcW.set(w('w'), str(widths[j])); tcW.set(w('type'), 'dxa')
                tcPr.insert(0, tcW)
                tb = etree.SubElement(tcPr, w('tcBorders'))
                if i == 0:
                    tb.append(pxml(w('<w:bottom w:val="single" w:sz="6" w:space="0" w:color="auto"/>')))
                else:
                    tb.append(pxml(w('<w:bottom w:val="none" w:sz="0" w:space="0"/>')))
                shd = etree.SubElement(tcPr, w('shd')); shd.set(w('val'), 'clear'); shd.set(w('fill'), 'auto')
                v_align = etree.SubElement(tcPr, w('vAlign'))
                v_align.set(w('val'), 'center')
                # Center compact labels and values; keep explanatory prose left aligned.
                for p in tc.findall(w('p')):
                    set_p_compact(p, TABLE_SZ)
                    cell_text = ''.join(p.itertext()).strip()
                    pPr = p.find(w('pPr'))
                    if pPr is None:
                        pPr = etree.SubElement(p, w('pPr'))
                    jc = pPr.find(w('jc'))
                    if jc is None:
                        jc = etree.SubElement(pPr, w('jc'))
                    short = len(cell_text) <= 12 and not any(c in cell_text for c in '，。；：、')
                    jc.set(w('val'), 'center' if (i == 0 or short) else 'left')
    return n

def set_p_compact(p, sz):
    pPr = p.find(w('pPr'))
    if pPr is None: pPr = etree.SubElement(p, w('pPr')) if len(p) else p.insert(0, etree.Element(w('pPr')))
    # remove extra spacing/indent set by style
    for tag in ('spacing', 'ind'):
        e = pPr.find(w(tag))
        if e is not None: pPr.remove(e)
    sp = pxml(w('<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>'))
    pPr.append(sp)
    for r in p.iter(w('r')):
        rPr = r.find(w('rPr'))
        if rPr is None:
            rPr = etree.Element(w('rPr')); r.insert(0, rPr)
        f = rPr.find(w('rFonts'))
        if f is None: f = etree.SubElement(rPr, w('rFonts'))
        f.set(w('ascii'), 'Times New Roman'); f.set(w('hAnsi'), 'Times New Roman')
        f.set(w('eastAsia'), 'SimSun'); f.set(w('cs'), 'Times New Roman')
        for tag in ('sz', 'szCs'):
            e = rPr.find(w(tag))
            if e is None: e = etree.SubElement(rPr, w(tag))
            e.set(w('val'), sz)

def math_norm(doc, sz=MATH_SZ):
    """every m:r gets w:rPr with body-size, no bold"""
    n = 0
    for om in doc.iter(mw('oMath')):
        for r in om.iter(mw('r')):
            n += 1
            rPr_old = r.find(mw('rPr'))
            ord_ = 1 if rPr_old is not None else 0
            old = r.find(w('rPr'))
            if old is not None: r.remove(old)
            rPr = pxml(w(
                '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math" w:eastAsia="SimSun"/>'
                '<w:sz w:val="%s"/><w:szCs w:val="%s"/></w:rPr>' % (sz, sz)))
            # w:rPr must come after m:rPr
            idx = list(r).index(rPr_old) + 1 if rPr_old is not None else 0
            r.insert(idx, rPr)
    return n

def front_matter(doc, title, subtitle, note, datestr):
    body = doc.find(w('body'))
    # find the trailing sectPr of the LAST section (direct child of body)
    last_sect = None
    for el in body:
        if el.tag == w('sectPr'): last_sect = el
    # copy page geometry from final sect
    pg = last_sect.find(w('pgSz')); mg = last_sect.find(w('pgMar'))
    geo = copy.deepcopy(pg).attrib if pg is not None else {}
    geo_m = copy.deepcopy(mg).attrib if mg is not None else {}
    def xml_attrs(attrs):
        parts = []
        for key, value in attrs.items():
            qn = etree.QName(key)
            name = ('w:' if qn.namespace == W else '') + qn.localname
            parts.append('%s="%s"' % (name, value))
        return ' '.join(parts)
    sect_xml = ('<w:sectPr xmlns:w="%s">' % W +
                ('<w:pgSz %s/>' % xml_attrs(geo)) +
                ('<w:pgMar %s/>' % xml_attrs(geo_m)) +
                '</w:sectPr>')
    brk = ('<w:sectPr xmlns:w="%s" %s/>' % (W, 'x'))  # placeholder unused
    def para(runs, jspacb=None, plain=False):
        return ('<w:p xmlns:w="%s"><w:pPr>%s<w:jc w:val="center"/></w:pPr>%s</w:p>' %
                (W, '', runs))
    def run(text, sz, bold=False, east='SimSun', space_before=0):
        b = '<w:b/>' if bold else ''
        return ('<w:r xmlns:w="%s"><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="%s"/>%s'
                '<w:sz w:val="%s"/><w:szCs w:val="%s"/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' %
                (W, east, b, sz, sz, text))
    def spacing(val):
        return ('<w:p xmlns:w="%s"><w:pPr><w:spacing w:after="%d"/></w:pPr></w:p>' % (W, val))
    def pbreak():
        return '<w:p xmlns:w="%s"><w:r><w:br w:type="page"/></w:r></w:p>' % W
    frag = []
    frag.append(spacing(3200))
    frag.append(para(run(title, '72', True), ))
    frag.append(spacing(600))
    frag.append(para(run(subtitle, '32', False)))
    frag.append(spacing(4400))
    frag.append(para(run(note, '24', False)))
    frag.append(spacing(200))
    frag.append(para(run(datestr, '24', False)))
    frag.append(pbreak())
    frag.append('<w:p xmlns:w="%s"><w:pPr><w:jc w:val="center"><w:sz w:val="64"/></w:jc></w:pPr></w:p>' % W)
    toc_head = ('<w:p xmlns:w="%s"><w:pPr><w:spacing w:after="240"/></w:pPr>'
               '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="SimHei"/>'
               '<w:b/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr><w:t xml:space="preserve">目　录</w:t></w:r></w:p>') % W
    frag.append(toc_head)
    toc_fld = ('<w:p xmlns:w="%s">'
               '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
               '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z </w:instrText></w:r>'
               '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
               '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:eastAsia="SimSun"/><w:sz w:val="24"/></w:rPr>'
               '<w:t xml:space="preserve">（打开文档后 Word 会自动更新目录；如未更新，全选后按 F9）</w:t></w:r>'
               '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>' % W)
    frag.append(toc_fld)
    frag.append(pbreak())
    # 閹栧畾 front section: page break paragraph w/ sectPr
    frag.append('<w:p xmlns:w="%s"><w:pPr>%s</w:pPr></w:p>' % (W, sect_xml))
    # insert at top of body
    for xmls in reversed(frag):
        el = etree.fromstring(xmls)
        body.insert(0, el)
    # body page numbering restart at 1
    if last_sect is not None:
        pgnum = last_sect.find(w('pgNumType'))
        if pgnum is None:
            pgnum = etree.Element(w('pgNumType'))
            # must be positioned per schema order; Word tolerant, append
            last_sect.append(pgnum)
        pgnum.set(w('start'), '1')
    return True

def ensure_updatefields(zin_members):
    name = 'word/settings.xml'
    sx = zin_members[name].decode('utf-8')
    if 'updateFields' not in sx:
        sx = sx.replace('<w:zoom', '<w:updateFields w:val="true"/><w:zoom', 1)
        if '<w:updateFields' not in sx:  # no zoom tag; insert after opening tag
            sx = re.sub(r'(<w:settings[^>]*>)', r'\1<w:updateFields w:val="true"/>', sx, count=1)
    zin_members[name] = sx.encode('utf-8')
    return zin_members

def rewrite(path, outpath, front=False, title='', subtitle='', note='', datestr=''):
    zin = zipfile.ZipFile(path)
    members = {n: zin.read(n) for n in zin.namelist()}
    zin.close()
    doc = etree.fromstring(members['word/document.xml'])
    # Pandoc's minimal reference document can contain empty page geometry
    # elements. Give every section an explicit A4 layout so Word and renderers
    # agree on the page size and margins.
    for sect in doc.iter(w('sectPr')):
        pg = sect.find(w('pgSz'))
        if pg is None:
            pg = etree.SubElement(sect, w('pgSz'))
        pg.set(w('w'), pg.get(w('w')) or '11906')
        pg.set(w('h'), pg.get(w('h')) or '16838')
        mg = sect.find(w('pgMar'))
        if mg is None:
            mg = etree.SubElement(sect, w('pgMar'))
        for name, value in [('top','1440'), ('right','1440'), ('bottom','1440'),
                            ('left','1440'), ('header','720'), ('footer','720'),
                            ('gutter','0')]:
            mg.set(w(name), mg.get(w(name)) or value)
    ntbl = three_line(doc)
    nmath = math_norm(doc)
    if front:
        front_matter(doc, title, subtitle, note, datestr)
    members['word/document.xml'] = etree.tostring(doc, xml_declaration=True, encoding='UTF-8', standalone=True)
    members = ensure_updatefields(members)
    with zipfile.ZipFile(outpath, 'w', zipfile.ZIP_DEFLATED) as z:
        for n_, b in members.items(): z.writestr(n_, b)
    return {'tables': ntbl, 'math_runs': nmath}

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('path'); ap.add_argument('outpath')
    ap.add_argument('--front', action='store_true')
    ap.add_argument('--title', default='递归自我改进')
    ap.add_argument('--subtitle', default='自我改进系统、模型侧优化与开放式智能体进化')
    ap.add_argument('--note', default='')
    ap.add_argument('--date', default='')
    a = ap.parse_args()
    print(rewrite(a.path, a.outpath, a.front, a.title, a.subtitle, a.note, a.date))
