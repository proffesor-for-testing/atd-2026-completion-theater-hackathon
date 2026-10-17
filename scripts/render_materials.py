from pathlib import Path
from xml.sax.saxutils import escape
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
PAGE_COUNTS = {}

root=Path(__file__).resolve().parents[1]
out=root/'docs'
pdfout=root/'materials'
pdfout.mkdir(exist_ok=True)
styles=getSampleStyleSheet()
navy=colors.HexColor('#080E62'); pink=colors.HexColor('#C91C53')
styles.add(ParagraphStyle(name='Body',fontName='Helvetica',fontSize=9.5,leading=13,spaceAfter=6))
styles.add(ParagraphStyle(name='H1x',fontName='Helvetica-Bold',fontSize=22,leading=26,textColor=navy,spaceAfter=15,keepWithNext=True))
styles.add(ParagraphStyle(name='H2x',fontName='Helvetica-Bold',fontSize=13,leading=17,textColor=navy,spaceBefore=12,spaceAfter=7,keepWithNext=True))
styles.add(ParagraphStyle(name='Cellx',fontName='Helvetica',fontSize=8.8,leading=11.8,spaceAfter=0))
styles.add(ParagraphStyle(name='CellHead',fontName='Helvetica-Bold',fontSize=8.8,leading=12,textColor=colors.white))

def inline(s):
    s=escape(s)
    s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'`([^`]+)`',r'<font name="Courier">\1</font>',s)
    # Display URLs as wrapped readable text, without tiny unbreakable lines.
    s=re.sub(r'(https?://\S+)',lambda m:m.group(1).replace('/','/<wbr/>').replace('-','-<wbr/>'),s)
    return s

def paragraph(s,style='Body'):
    return Paragraph(inline(s),styles[style])

def table(rows):
    count=len(rows[0]); width=A4[0]-92
    if rows[0][0]=='Time (CET)': widths=[width*.22,width*.09,width*.40,width*.29]
    elif rows[0][:3]==['Pattern','The claim','The check']:widths=[width*.20,width*.25,width*.55]
    elif count==2: widths=[width*.18,width*.82]
    elif count==3: widths=[width*.17,width*.58,width*.25]
    elif count==4: widths=[width*.12,width*.51,width*.12,width*.25]
    elif count==5: widths=[width*.17,width*.12,width*.35,width*.14,width*.22]
    elif count==6: widths=[width*.12,width*.16,width*.2,width*.16,width*.16,width*.2]
    else: widths=[width/count]*count
    data=[[paragraph(c,'CellHead' if i==0 else 'Cellx') for c in row] for i,row in enumerate(rows)]
    t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),1,pink),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#F2F4F8'),colors.white]),('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#D6DBE4'))]))
    return t

def parse(path):
    lines=path.read_text().splitlines(); story=[]; i=0
    compact=path.name=='06-Pattern-Reference-Card.md'
    body=ParagraphStyle(name='CompactBody',parent=styles['Body'],fontSize=9.4,leading=12,spaceAfter=5) if compact else styles['Body']
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1; continue
        if line=='---': story.append(PageBreak());i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in row):rows.append(row)
                i+=1
            story.extend([table(rows),Spacer(1,8)]);continue
        if line.startswith('# '):story.append(paragraph(line[2:],'H1x'))
        elif line.startswith('## '):
            if line=='## Finding or bounded clean investigation':story.append(PageBreak())
            story.append(paragraph(line[3:],'H2x'))
        elif line.startswith('- '):story.append(paragraph('[ ] '+line[6:] if line.startswith('- [ ] ') else '- '+line[2:]))
        else:story.append(Paragraph(inline(line),body))
        i+=1
    return story

def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(pink);canvas.setLineWidth(.7)
    canvas.line(46,38,A4[0]-46,38);canvas.setFont('Helvetica',8);canvas.setFillColor(navy)
    canvas.drawString(46,25,'Agile Testing Days 2026   /   Completion Theater Hackathon')
    canvas.drawRightString(A4[0]-46,25,str(doc.page));canvas.restoreState()

def create(name,files):
    story=[]
    for i,f in enumerate(files):
        if i:story.append(PageBreak())
        story+=parse(out/f)
    doc=SimpleDocTemplate(str(pdfout/name),pagesize=A4,rightMargin=46,leftMargin=46,topMargin=42,bottomMargin=52,title=name[:-4].replace('-',' '),author='Dragan Spiridonov and Lalitkumar Bhamare')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    PAGE_COUNTS[name] = doc.page
    return pdfout/name

sources=['01-Starter-PRD.md','02-Verification-Checklist.md','03-Cross-Audit-Checklist.md','04-Scoring-Sheets.md','05-Facilitator-Notes.md']
for f in sources:create(f.replace('.md','.pdf'),[f])
create('Participant-Pack.pdf',['01-Starter-PRD.md','02-Verification-Checklist.md','03-Cross-Audit-Checklist.md','04-Scoring-Sheets.md','06-Pattern-Reference-Card.md'])
create('Facilitator-Pack.pdf',['05-Facilitator-Notes.md','04-Scoring-Sheets.md'])
for name, pages in PAGE_COUNTS.items():
    assert pages > 0
    print(name, pages, 'pages', (pdfout/name).stat().st_size, 'bytes')
