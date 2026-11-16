"""Which w:jc value puts an RTL Word paragraph against the right edge?"""
import os
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE = os.path.dirname(os.path.abspath(__file__))
doc = Document()
section = doc.sections[0]
section.page_width, section.page_height = Pt(500), Pt(300)
section.left_margin = section.right_margin = Pt(20)

for label, align, bidi in (("RIGHT+bidi", WD_ALIGN_PARAGRAPH.RIGHT, True),
                           ("LEFT+bidi", WD_ALIGN_PARAGRAPH.LEFT, True),
                           ("RIGHT only", WD_ALIGN_PARAGRAPH.RIGHT, False)):
    p = doc.add_paragraph()
    if bidi:
        p._p.get_or_add_pPr().append(OxmlElement("w:bidi"))
    run = p.add_run("علامة " + label)
    run.font.size = Pt(14)
    rPr = run._element.get_or_add_rPr()
    rPr.append(OxmlElement("w:rtl"))
    p.alignment = align

doc.save(os.path.join(HERE, "align.docx"))
print("written")
