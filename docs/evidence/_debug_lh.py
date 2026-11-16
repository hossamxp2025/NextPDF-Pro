import sys, os
sys.path.insert(0, os.getcwd())
import pymupdf as fitz

def make(path, lh, shade=True, fontsize=11):
    doc = fitz.open(); page = doc.new_page(width=595, height=520)
    headers = ["Date", "Description", "Amount"]
    rows = [["2026-11-01","Opening balance","1,200.00"],
            ["2026-11-02","Groceries","85.50"],
            ["2026-11-03","Salary","3,000.00"],
            ["2026-11-04","Fuel","120.75"]]
    cols=[40,200,380]; top=60
    if shade:
        for i in range(len(rows)+1):
            y0=top+i*lh
            if i%2==0:
                page.draw_rect(fitz.Rect(30,y0,560,y0+lh), color=None, fill=(0.92,0.92,0.92), width=0)
    for c,h in zip(cols,headers): page.insert_text((c, top+fontsize+3), h, fontsize=fontsize+1)
    for ri,row in enumerate(rows,1):
        for c,v in zip(cols,row): page.insert_text((c, top+ri*lh+fontsize+3), v, fontsize=fontsize)
    doc.save(path); doc.close()

for lh in (16, 18, 20, 22, 24, 28):
    p = f"docs/evidence/_lh_{lh}.pdf"
    make(p, lh)
    d = fitz.open(p); pg = d[0]
    ft = pg.find_tables(use_layout=False, strategy="text", min_words_vertical=3)
    print(f"lh={lh}: tables={len(ft.tables)} rows={[t.row_count for t in ft.tables]}")
    if ft.tables:
        for i, row in enumerate(ft.tables[0].rows[:8]):
            txt = [pg.get_textbox(fitz.Rect(c)).strip().replace('\n','/') if c else '' for c in row.cells]
            print(f"   r{i}: {txt}")
    d.close()
