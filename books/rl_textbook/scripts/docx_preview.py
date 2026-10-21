"""用 Word COM 把 .docx 转成 PDF（本机没有 LibreOffice），再渲染若干页做视觉核验。"""
import os
import sys

import fitz

DOCX = sys.argv[1] if len(sys.argv) > 1 else r"output\docx\03_DP与TD.docx"
PAGES = [int(x) for x in (sys.argv[2].split(",") if len(sys.argv) > 2 else ["1", "2"])]

docx_path = os.path.abspath(DOCX)
pdf_path = os.path.splitext(docx_path)[0] + ".pdf"

import win32com.client  # noqa: E402

word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0
try:
    doc = word.Documents.Open(docx_path, ReadOnly=False, AddToRecentFiles=False)
    doc.SaveAs(pdf_path, FileFormat=17)     # wdFormatPDF
    doc.Close(SaveChanges=0)
finally:
    word.Quit()

d = fitz.open(pdf_path)
print("pages:", d.page_count, "size MB:", round(os.path.getsize(pdf_path) / 1048576, 2))
for pno in PAGES:
    if 1 <= pno <= d.page_count:
        out = os.path.join("cache", f"_docx_p{pno}.png")
        d[pno - 1].get_pixmap(dpi=110).save(out)
        print("rendered", out)
