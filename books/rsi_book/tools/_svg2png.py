import fitz, sys
f = fitz.open(sys.argv[1])
if not f.is_pdf:
    pdf = f.convert_to_pdf()
    f = fitz.open(stream=pdf, filetype='pdf')
pg = f[0]
pg.get_pixmap(dpi=220).save(sys.argv[2])
