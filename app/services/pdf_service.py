from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

class PDFService:
    @staticmethod
    def generate_ticket_pdf(ticket):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # 1. Header / Title
        story.append(Paragraph(f"Ticket Details: {ticket.id}", title_style))
        story.append(Spacer(1, 12))

        # 2. Main Info Table
        data = [
            ["Subject", ticket.title or ticket.subject or ""],
            ["Category", ticket.category or ""],
            ["Priority", ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority)],
            ["Status", ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)],
            ["Assigned Team", ticket.team.name if ticket.team else "Unassigned"],
            ["Assigned User", ticket.assignee.full_name if ticket.assignee else "Unassigned"],
            ["Created By", ticket.creator.full_name if ticket.creator else "Unknown"],
            ["Created At", ticket.created_at.strftime('%Y-%m-%d %H:%M:%S') if ticket.created_at else "N/A"],
        ]

        t = Table(data, colWidths=[120, 350])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (1, 0), (1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.white),
        ]))
        story.append(t)
        story.append(Spacer(1, 24))

        # 3. Description
        story.append(Paragraph("Description", heading_style))
        story.append(Paragraph(ticket.description, normal_style))
        story.append(Spacer(1, 24))

        # 4. Comments
        story.append(Paragraph("Comments", heading_style))
        if ticket.comments:
            for comment in ticket.comments:
                author = comment.author.full_name if comment.author else "Unknown"
                date_str = comment.created_at.strftime('%Y-%m-%d %H:%M')
                story.append(Paragraph(f"<b>{author}</b> ({date_str}):", normal_style))
                story.append(Paragraph(comment.text, normal_style))
                story.append(Spacer(1, 8))
        else:
            story.append(Paragraph("No comments.", normal_style))
        story.append(Spacer(1, 24))

        # 5. Activity Log (Status History)
        story.append(Paragraph("Activity Log", heading_style))
        if ticket.status_history:
            history_data = [["Date", "Action", "User"]]
            for h in ticket.status_history:
                date_str = h.changed_at.strftime('%Y-%m-%d %H:%M')
                action = f"{h.old_status.value} -> {h.new_status.value}" if h.old_status else f"Created ({h.new_status.value})"
                user = h.changed_by.full_name if h.changed_by else "System"
                history_data.append([date_str, action, user])
            
            h_table = Table(history_data, colWidths=[120, 200, 150])
            h_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(h_table)
        else:
            story.append(Paragraph("No activity recorded.", normal_style))

        
        doc.build(story)
        buffer.seek(0)
        return buffer
    @staticmethod
    def generate_user_report(user, tickets, comments):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # 1. Header
        story.append(Paragraph(f"User Data Report: {user.full_name}", title_style))
        from datetime import datetime
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
        story.append(Spacer(1, 12))

        # 2. User Profile
        story.append(Paragraph("User Profile", heading_style))
        profile_data = [
            ["Data Point", "Value"],
            ["Full Name", user.full_name],
            ["Email", user.email],
            ["Role", user.role.value],
            ["Department", user.department or "N/A"],
            ["Joined", user.created_at.strftime('%Y-%m-%d') if user.created_at else "N/A"]
        ]
        
        t_profile = Table(profile_data, colWidths=[120, 350])
        t_profile.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(t_profile)
        story.append(Spacer(1, 24))

        # 3. Ticket Summary
        story.append(Paragraph(f"Ticket Summary ({len(tickets)} Total)", heading_style))
        if tickets:
            ticket_data = [["ID", "Title", "Status", "Date"]]
            for t in tickets:
                ticket_data.append([
                    str(t.id),
                    t.title[:40] + "..." if len(t.title) > 40 else t.title,
                    t.status.value,
                    t.created_at.strftime('%Y-%m-%d')
                ])
            
            t_tickets = Table(ticket_data, colWidths=[40, 250, 80, 80])
            t_tickets.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
            ]))
            story.append(t_tickets)
        else:
            story.append(Paragraph("No tickets found.", normal_style))
        story.append(Spacer(1, 24))

        # 4. Recent Comments
        story.append(Paragraph(f"Recent Comments ({len(comments)} Total)", heading_style))
        if comments:
            # Show last 20 comments to avoid huge PDFs
            active_comments = comments[:20] 
            for c in active_comments:
                story.append(Paragraph(f"<b>Ticket #{c.ticket_id}</b> - {c.created_at.strftime('%Y-%m-%d %H:%M')}", normal_style))
                story.append(Paragraph(c.text, normal_style))
                story.append(Spacer(1, 8))
            
            if len(comments) > 20:
                 story.append(Paragraph(f"...and {len(comments) - 20} more comments.", normal_style))
        else:
             story.append(Paragraph("No comments found.", normal_style))

        doc.build(story)
        buffer.seek(0)
        return buffer
