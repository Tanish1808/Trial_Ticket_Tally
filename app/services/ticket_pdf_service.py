import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from datetime import datetime
from html import escape

class TicketPdfService:
    @staticmethod
    def generate_ticket_pdf(ticket):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Custom Title Style
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#6366f1')
        )

        def safe_p(text):
            return escape(str(text)) if text else ""

        # Header
        elements.append(Paragraph(f"Ticket Summary: #{ticket.id}", title_style))
        elements.append(Paragraph(f"Generated on {datetime.utcnow().strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(Spacer(1, 20))

        # Ticket Details Table
        data = [
            ['Field', 'Value'],
            ['Subject', safe_p(ticket.title)],
            ['Status', ticket.status.value],
            ['Priority', ticket.priority.value],
            ['Category', ticket.category],
            ['Created At', ticket.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Assigned To', safe_p(ticket.assignee.full_name) if ticket.assignee else 'Unassigned']
        ]

        t = Table(data, colWidths=[150, 300])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        elements.append(t)
        elements.append(Spacer(1, 20))

        # Description
        elements.append(Paragraph("Description:", styles['Heading2']))
        elements.append(Paragraph(safe_p(ticket.description), styles['Normal']))
        elements.append(Spacer(1, 20))

        # History
        if ticket.status_history:
            elements.append(Paragraph("Status History:", styles['Heading2']))
            history_data = [['Old Status', 'New Status', 'Changed On']]
            for h in ticket.status_history:
                history_data.append([
                    h.old_status.value if h.old_status else "None", 
                    h.new_status.value, 
                    h.changed_at.strftime('%Y-%m-%d %H:%M')
                ])
            
            ht = Table(history_data, colWidths=[150, 150, 150])
            ht.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            elements.append(ht)

        # Footer
        elements.append(Spacer(1, 40))
        elements.append(Paragraph("Thank you for using Ticket Tally Support System.", styles['Italic']))

        doc.build(elements)
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content
