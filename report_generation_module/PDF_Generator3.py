from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime
import json
import re
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from report_generation_module.plot_generator import generate_radar_chart

pdfmetrics.registerFont(TTFont('Arial', 'fonts/ARIAL.TTF'))
pdfmetrics.registerFont(TTFont('Arial-Bold', 'fonts/ArialBD.ttf'))
styles = getSampleStyleSheet()
styles['BodyText'].fontName = 'Arial'

def create_combined_pdf(logo_path, json_path, scores_json_path, quality_json_path, presentation_json_path, output_pdf_path , graph_path):
    with open(presentation_json_path, "r") as file:
        data = json.load(file)
    presentation_mode = data.get("presentation_mode", False)
    logo_path = r'D:\SOME CLOUD\SOME-Grading-Automation\static\SoME Logo.png'
    with open(json_path, 'r') as fp:
        tabular_data = json.load(fp)
    with open(scores_json_path, 'r') as fp:
        quality_data = json.load(fp)
        midval = list(quality_data.values())
    if presentation_mode == 'on':
        llm_questions = [
            "Questions",
            "Did the Speaker Speak with Confidence ?",
            "Did the speaker vary their tone, speed, volume while delivering the speech/presentation? ",
            "Did they use any gestures with their hands or body while speaking?",
            "Did they have expressions on their faces?",
            "Did the speech have a structure of Opening, Body and Conclusion? ",
            "Did the speaker keep the presentation engaging by adding relevant examples, anecdotes and data to back their content?   ",
            "Was the overall “Objective” of the speech delivered clearly?",
            "Was the content of the presentation/speech to the point, or did it include unnecessary details that may have distracted or confused the audience?",
            "Was the content of the presentation/speech relevant to the objective of the presentation?",
            "Was the content of the presentation/speech clear and easy to understand?",
            "Did the speaker demonstrate credibility? Will you trust the speaker? ",
            "Did the speaker explain how the speech or topic of the presentation would benefit the audience and what they could gain from it?",
            "Did the speaker make an emotional connection with the audience ? ",
            "Overall, were you convinced/ persuaded with the speaker’s view on the topic?"
        ]
    else:
        llm_questions = [
            "Questions",
            "Did the Speaker Speak with Confidence ?",
            "Did the speaker vary their tone, speed, volume?",
            "Did they use any gestures with their hands or body while speaking? ",
            "Did they have expressions on their faces?",
            "Who are you and what are your skills, expertise, personality traits ?",
            "Why are you the best person to fit this role?",
            "How are you different from others? ",
            "What value do you bring to the role?",
            "Did the speech have a structure of Opening, Body and Conclusion?",
            "How was the quality of research for the topic? Did the student’s speech demonstrate a good depth? Did they cite the sources of research properly?",
            "How creatively did the student present the video?",
            "How convinced were you with the overall speech on the topic? Was it persuasive? Will you give them the job/opportunity? "
        ]

    def clean_answer(answer):
        return re.sub(r'^\d+\.\s*', '', answer).strip()

    llm_answers = []
    if 'LLM' in tabular_data:
        llm_answers = re.split(r'\n(?=\d+[.)])', tabular_data['LLM'])
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter, topMargin=1.5*inch, bottomMargin=0.8*inch)
    flowables = []
    styles = getSampleStyleSheet()

    def add_header_footer(canvas, doc):
        canvas.saveState()
        logo = Image(logo_path, width=2*inch, height=1*inch)
        logo.drawOn(canvas, (letter[0]-2*inch)/2, letter[1]-1.2*inch)
        website_text = "https://some.education"
        canvas.setFont("Arial", 9)
        canvas.linkURL("https://some.education", (0.5*inch, 0.3*inch, 2.5*inch, 0.5*inch), relative=1)
        canvas.drawString(0.5*inch, 0.3*inch, website_text)
        page_num = canvas.getPageNumber()
        canvas.drawRightString(letter[0]-0.5*inch, 0.3*inch, f"Page {page_num}")
        canvas.restoreState()

    section_style = ParagraphStyle('SectionStyle', parent=styles['BodyText'], fontName='Arial-Bold', fontSize=10, spaceAfter=12, leading=16)
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['BodyText'], fontSize=10, leading=14, spaceAfter=6, leftIndent=10)
    name = tabular_data.get('User Name', 'Unknown Candidate')
    now = datetime.now()
    with open(scores_json_path, "r") as file:
        data = json.load(file)
    score = sum(data.values())
    formatted_date = now.strftime("%d %B %Y")
    title = Paragraph(
        f"<para alignment='center'><b>{name}</b><br/></para>"
        f"<para alignment='center'>{formatted_date}</para>", 
        styles['Title']
    )
    flowables.append(title)
    flowables.append(Spacer(1, 24))
    iq_style = ParagraphStyle('IQStyle', parent=styles['BodyText'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=12)
    if presentation_mode == "on":
        iq_style = ParagraphStyle(
            'IQStyle',
            parent=styles['BodyText'],
            fontName='Helvetica-Bold',
            fontSize=14,      # slightly larger
            spaceAfter=12
        )
        print("Printing Scores , " , score)


        flowables.append(
            Paragraph(f"<b>Influence Quotient: {(round(score/65 * 100))}/100</b>", iq_style)
        )
        flowables.append(Spacer(1, 16))
    else:
        print("Printing Scores , " , score)
        iq_style = ParagraphStyle(
            'IQStyle',
            parent=styles['BodyText'],
            fontName='Helvetica-Bold',
            fontSize=14,      # slightly larger
            spaceAfter=12
        )


        flowables.append(
            Paragraph(f"<b>Influence Quotient: {round((score / 50 * 100))}/100</b>", iq_style)
        )
        flowables.append(Spacer(1, 16))
    chart_path = f"output_{os.path.basename(json_path).split('.')[0]}.png"
    try:
        generate_radar_chart(presentation_json_path , graph_path , scores_json_path , chart_path)
        chart_img = Image(chart_path, width=4.5*inch, height=3*inch)
        flowables.append(Paragraph("Overall Evaluation Summary", section_style))
        flowables.append(chart_img)
        flowables.append(Spacer(1, 18))
    except Exception as e:
        print(f"Error generating radar chart: {e}")
        flowables.append(Paragraph("Overall Evaluation Summary (Chart unavailable)", section_style))
        flowables.append(Spacer(1, 18))

    def add_quality_section(title, items):
        flowables.append(Paragraph(title, section_style))
        for item in items:
            flowables.append(Paragraph(f"• {item}", bullet_style))
        flowables.append(Spacer(1, 18))

    try:
        with open(quality_json_path, 'r') as fp:
            quality_data = json.load(fp)
        add_quality_section("Qualitative Analysis - Positive", quality_data["Qualitative Analysis"])
        add_quality_section("Qualitative Analysis - Areas of Improvement", quality_data["Quantitative Analysis"])
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
            Paragraph("<b>5 point Scale</b>", bold_style),
            Paragraph("<b>Remarks / Feedback</b>", bold_style)
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
                    scores.append("Poor")
            scores_text = "<br/>" + "<br/>".join([f"<b>{score}</b>" for score in scores])
            table_data.append([
                Paragraph(f"{i}.", normal_style),
                Paragraph(items_text, normal_style),
                Paragraph(str(midval[i - 1]), normal_style),
                Paragraph(scores_text, normal_style)
            ])
        else:
            answer_index = i if i < len(llm_answers) else None
            answer = clean_answer(llm_answers[answer_index]) if answer_index is not None else "N/A"
            table_data.append([
                Paragraph(f"{i}.", normal_style),
                Paragraph(question, normal_style),
                Paragraph(str(midval[i - 1]), normal_style),
                Paragraph(answer, normal_style)
            ])
    table = Table(table_data, colWidths=[40, 250, 80, 200])
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
    doc.build(flowables, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    print("PDF generated successfully with dynamic table!")