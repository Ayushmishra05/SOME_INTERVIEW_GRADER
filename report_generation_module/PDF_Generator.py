from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
import json
import re
import math
import os 
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from LLM_Module.Overall_Analyser import VideoResumeEvaluator 
from config import save_path

pdfmetrics.registerFont(TTFont('Arial', r'ARIAL.TTF'))
pdfmetrics.registerFont(TTFont('Arial-Bold', r'ArialBD.ttf'))
styles = getSampleStyleSheet()
styles['BodyText'].fontName = 'Arial'

def create_combined_pdf(logo_path, json_path):
    with open(json_path, 'r') as fp:
        tabular_data = json.load(fp)

    llm_questions = [
        "Questions", 
        "Did the Speaker Speak with Confidence ?", 
        "Was the content interesting and as per the guidelines provided?",
        "Who are you and what are your skills, expertise, and personality traits?",
        "Why are you the best person to fit this role?",
        "How are you different from others?",
        "What value do you bring to the role?",
        "Did the speech have a structure of Opening, Body, and Conclusion?",
        "Did the speaker vary their tone, speed, and volume while delivering the speech/presentation?", 
        "How was the quality of research for the topic? Did the speech demonstrate good depth? Did they cite sources?",
        "How convinced were you with the overall speech on the topic? Was it persuasive? Will you consider them for the job/opportunity?"
    ]

    def clean_answer(answer):
        return re.sub(r'^\d+\.\s*', '', answer).strip()

    llm_answers = []
    if 'LLM' in tabular_data:
        llm_answers = re.split(r'\n(?=\d+\.)', tabular_data['LLM'])

    doc = SimpleDocTemplate("reports/combined_report.pdf", 
                            pagesize=letter,
                            topMargin=1.5*inch,
                            bottomMargin=0.8*inch)
    flowables = []
    styles = getSampleStyleSheet()

    def add_header_footer(canvas, doc):
        canvas.saveState()
        logo = Image(logo_path, width=2*inch, height=1*inch)
        logo.drawOn(canvas, (letter[0]-2*inch)/2, letter[1]-1.2*inch)
        website_text = "https://some.education"
        canvas.setFont("Arial", 9)
        canvas.linkURL("https://some.education",
                       (0.5*inch, 0.3*inch, 2.5*inch, 0.5*inch),
                       relative=1)
        canvas.drawString(0.5*inch, 0.3*inch, website_text)
        page_num = canvas.getPageNumber()
        canvas.drawRightString(letter[0]-0.5*inch, 0.3*inch, f"Page {page_num}")
        canvas.restoreState()

    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['BodyText'],
        fontName='Arial-Bold',
        fontSize=10,
        spaceAfter=12,
        leading=16
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
        leftIndent=10
    )

    name = tabular_data.get('User Name', 'Unknown Candidate')
    now = datetime.now()
    formatted_date = now.strftime("%d %B %Y")
    title = Paragraph(
        f"<para alignment='center'><b>{name}</b><br/></para>"
        f"<para alignment='center'>{formatted_date}</para>", 
        styles['Title']
    )
    flowables.append(title)
    flowables.append(Spacer(1, 24))

    def add_quality_section(title, items):
        flowables.append(Paragraph(title, section_style))
        bullet_list = []
        for item in items:
            bullet_list.append(Paragraph(f"• {item}", bullet_style))
        flowables.extend(bullet_list)
        flowables.append(Spacer(1, 18))
    
    try:
        with open(r'json/quality_analysis.json', 'r') as fp:
            quality_data = json.load(fp)
        add_quality_section("Qualitative Analysis - Positive", quality_data["Qualitative Analysis"])
        add_quality_section("Qualitative Analysis - Areas of Imrpovement", quality_data["Quantitative Analysis"])
    except:
        pass


    flowables.append(Spacer(1, 18))
    flowables.append(PageBreak())

    section_style = ParagraphStyle('SectionStyle', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=10, spaceAfter=12, leading=16)
    flowables.append(Paragraph("<b>Detailed Evaluation Metrics</b>", section_style))
    flowables.append(Spacer(1, 24))

    normal_style = ParagraphStyle('NormalStyle', parent=styles['BodyText'], fontSize=10, leading=12, spaceAfter=6)
    bold_style = ParagraphStyle('BoldStyle', parent=normal_style, fontName='Helvetica-Bold')

    table_data = [
        [
            Paragraph("<b>No.</b>", bold_style),
            Paragraph("<b>Items to look out for</b>", bold_style),
            Paragraph("<b>5 point scale / Answer</b>", bold_style)
        ]
    ]

    for i, question in enumerate(llm_questions[1:], 1):
        if i == 1:
            sub_items = [
                ("Posture", "posture"),
                ("Smile", "Smile Score"),
                ("Eye Contact", "Eye Contact"),
                ("Energetic Start", "Energetic Start")
            ]
            items_text = "Did the speaker speak with confidence?<br/>" + "<br/>".join([f"• {item[0]}" for item in sub_items])
            scores = []
            for item in sub_items:
                key = item[1]
                metric_value = tabular_data.get(key)
                if metric_value == 1:
                    scores.append("Needs Improvement")
                elif metric_value == 2:
                    scores.append("Poor")
                elif metric_value == 3:
                    scores.append("Satisfactory")
                elif metric_value == 4:
                    scores.append("Good")
                elif metric_value == 5:
                    scores.append("Excellent")
                else:
                    scores.append("N/A")
            scores_text = "<br/>" + "<br/>".join([f"<b>{score}</b>" for score in scores])
            table_data.append([
                Paragraph(f"{i}.", normal_style),
                Paragraph(items_text, normal_style),
                Paragraph(scores_text, normal_style)
            ])
        # elif i == 10:
        #     # Override Q10 to use only computed audio metrics.
        #     avg_vol = tabular_data.get("average_volume", 0)
        #     vol_std = tabular_data.get("volume_std", 0)
        #     speed = tabular_data.get("speaking_speed", tabular_data.get("words_per_minute", 0))
        #     speed_std = tabular_data.get("speed_std", tabular_data.get("pace_std", 0))
        #     predicted_tone = tabular_data.get("predicted_tone", "unknown")
        #     volume_percentage = ((avg_vol + 60) / 60) * 100 if avg_vol != float('-inf') else 0
        #     answer = (f"Average Volume: {avg_vol:.2f} dBFS, Volume Std Dev: {vol_std:.2f} dB, "
        #               f"Speaking Speed: {speed:.2f} wpm, Speed Std Dev: {speed_std:.2f} wpm, "
        #               f"Predicted Tone: {predicted_tone}")
        #     table_data.append([
        #         Paragraph(f"{i}.", normal_style),
        #         Paragraph(question, normal_style),
        #         Paragraph(answer, normal_style)
        #     ])
        else:
            answer_index = i if i < len(llm_answers) else None
            if answer_index is not None:
                answer = clean_answer(llm_answers[answer_index])
            else:
                answer = "N/A"
            table_data.append([
                Paragraph(f"{i}.", normal_style),
                Paragraph(question, normal_style),
                Paragraph(answer, normal_style)
            ])

    from reportlab.platypus import Table
    table = Table(table_data, colWidths=[40, 300, 200])
    table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('TOPPADDING', (0,1), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    flowables.append(table)

    doc.build(flowables, 
              onFirstPage=add_header_footer,
              onLaterPages=add_header_footer)

    print("PDF generated successfully with dynamic table!")
    os.remove(save_path)




# if __name__ == "__main__":
#     create_combined_pdf(r"logos\logo.png" , r"json\output.json")