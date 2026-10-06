"""
Official College Attendance PDF Report Generator
Generates clean, printable, formal PDF reports containing:
1. College Name
2. Attendance Report Header & Date Range
3. Table: Date | Staff Name | Staff ID | In Time | Out Time | Status
4. Attendance Status Summary (Total Records, Present, Absent, Half Day, Rate)

Built with ReportLab.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for accurate 'Page X of Y' footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Bottom divider
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.75)
        self.line(36, 40, 612 - 36, 40)

        # Footer text
        self.drawString(36, 28, "Official Institutional Attendance Record")
        self.drawRightString(612 - 36, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def format_report_date(d_str):
    """Converts YYYY-MM-DD into readable DD Mon YYYY."""
    try:
        dt = datetime.strptime(d_str, "%Y-%m-%d")
        return dt.strftime("%d %b %Y")
    except Exception:
        return d_str

class PDFReportGenerator:
    def __init__(self, filename="Attendance_Report.pdf", college_name="COLLEGE OF ENGINEERING & TECHNOLOGY"):
        self.filename = filename
        self.college_name = college_name

    def generate(self, start_date, end_date, rows, stats=None, department="All"):
        doc = SimpleDocTemplate(
            self.filename,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=50
        )

        styles = getSampleStyleSheet()

        # Styles
        style_college = ParagraphStyle(
            'CollegeName',
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#0F172A"),
            alignment=1, # Center
            spaceAfter=4
        )

        style_title = ParagraphStyle(
            'ReportTitle',
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2563EB"),
            alignment=1,
            spaceAfter=3
        )

        style_range = ParagraphStyle(
            'DateRange',
            fontName='Helvetica',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#475569"),
            alignment=1,
            spaceAfter=12
        )

        style_th = ParagraphStyle(
            'TH',
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
            alignment=0
        )

        style_th_center = ParagraphStyle(
            'TH_Center',
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
            alignment=1
        )

        style_td = ParagraphStyle(
            'TD',
            fontName='Helvetica',
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#0F172A")
        )

        style_td_center = ParagraphStyle(
            'TD_Center',
            fontName='Helvetica',
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#0F172A"),
            alignment=1
        )

        style_sum_heading = ParagraphStyle(
            'SumHeading',
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=4
        )

        style_sum_th = ParagraphStyle(
            'SumTH',
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=11,
            alignment=1
        )

        style_sum_val = ParagraphStyle(
            'SumVal',
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0F172A"),
            alignment=1
        )

        story = []

        # 1. College Name
        story.append(Paragraph(self.college_name.upper(), style_college))

        # 2. Report Subtitle
        story.append(Paragraph("Attendance Report", style_title))

        # 3. Date Range
        range_str = f"Date Range: {format_report_date(start_date)} to {format_report_date(end_date)}"
        if department and department != "All":
            range_str += f" &nbsp;•&nbsp; Department: {department}"
        story.append(Paragraph(range_str, style_range))

        # 4. Table: Columns with Status at the end
        # Total Width = 540 pt (Letter width 612 - 72 = 540)
        # Date: 80, Staff Name: 180, Staff ID: 60, In Time: 75, Out Time: 75, Status: 70
        col_widths = [80, 180, 60, 75, 75, 70]

        table_data = [
            [
                Paragraph("Date", style_th),
                Paragraph("Staff Name", style_th),
                Paragraph("Staff ID", style_th_center),
                Paragraph("In Time", style_th_center),
                Paragraph("Out Time", style_th_center),
                Paragraph("Status", style_th_center)
            ]
        ]

        for r in rows:
            date_disp = format_report_date(str(r.get('date', '')))
            name_disp = str(r.get('name', ''))
            id_disp = str(r.get('user_id', ''))
            in_disp = str(r.get('first_in') or '--')
            out_disp = str(r.get('last_out') or '--')
            status_val = str(r.get('status') or 'Absent')

            if status_val == 'Present':
                status_p = Paragraph("<font color='#059669'><b>Present</b></font>", style_td_center)
            elif status_val == 'Half Day':
                status_p = Paragraph("<font color='#D97706'><b>Half Day</b></font>", style_td_center)
            elif status_val == 'Absent':
                status_p = Paragraph("<font color='#DC2626'><b>Absent</b></font>", style_td_center)
            else:
                status_p = Paragraph(f"<font color='#475569'><b>{status_val}</b></font>", style_td_center)

            table_data.append([
                Paragraph(date_disp, style_td),
                Paragraph(name_disp, style_td),
                Paragraph(id_disp, style_td_center),
                Paragraph(in_disp, style_td_center),
                Paragraph(out_disp, style_td_center),
                status_p
            ])

        # Fallback if no records
        if len(rows) == 0:
            table_data.append([
                Paragraph("No attendance records found for this period.", style_td_center),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td),
                Paragraph("", style_td)
            ])

        t = Table(table_data, colWidths=col_widths, repeatRows=1)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]
        
        # Alternating row colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor("#F8FAFC")))
            else:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.white))

        t.setStyle(TableStyle(t_style))
        story.append(t)
        story.append(Spacer(1, 14))

        # 5. Attendance Status Summary at the End (Present, Absent, Half Day)
        total_records = len(rows)
        present_count = sum(1 for r in rows if r.get('status') == 'Present')
        absent_count = sum(1 for r in rows if r.get('status') == 'Absent')
        half_day_count = sum(1 for r in rows if r.get('status') == 'Half Day')
        rate = round(((present_count + 0.5 * half_day_count) / total_records * 100), 1) if total_records > 0 else 0.0

        story.append(Paragraph("<b>ATTENDANCE STATUS SUMMARY</b>", style_sum_heading))
        story.append(Spacer(1, 3))

        sum_table_data = [
            [
                Paragraph("<font color='#475569'>TOTAL RECORDS</font>", style_sum_th),
                Paragraph("<font color='#059669'>PRESENT</font>", style_sum_th),
                Paragraph("<font color='#DC2626'>ABSENT</font>", style_sum_th),
                Paragraph("<font color='#D97706'>HALF DAY</font>", style_sum_th),
                Paragraph("<font color='#2563EB'>ATTENDANCE RATE</font>", style_sum_th)
            ],
            [
                Paragraph(f"<b>{total_records}</b>", style_sum_val),
                Paragraph(f"<b><font color='#059669'>{present_count}</font></b>", style_sum_val),
                Paragraph(f"<b><font color='#DC2626'>{absent_count}</font></b>", style_sum_val),
                Paragraph(f"<b><font color='#D97706'>{half_day_count}</font></b>", style_sum_val),
                Paragraph(f"<b><font color='#2563EB'>{rate}%</font></b>", style_sum_val)
            ]
        ]
        t_sum = Table(sum_table_data, colWidths=[108, 108, 108, 108, 108])
        t_sum.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(t_sum)
        doc.build(story, canvasmaker=NumberedCanvas)
        return self.filename
