from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

class PDFService:
    @staticmethod
    def generate_ticket_pdf(ticket):
        """Generates a detailed PDF report for a single ticket, including comments and timeline.

        Args:
            ticket (Ticket): The Ticket database model instance.

        Returns:
            BytesIO: A binary stream containing the generated PDF report.
        """
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
        """Generates a comprehensive PDF report summarizing a user's profile, tickets, and comments.

        Args:
            user (User): The User database model instance.
            tickets (list): A list of Ticket database model instances.
            comments (list): A list of Comment database model instances.

        Returns:
            BytesIO: A binary stream containing the generated PDF report.
        """
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

    @staticmethod
    def generate_performance_report(staff_list):
        """Generates a PDF performance report for IT staff members.

        Args:
            staff_list (list): List of dicts representing staff metrics.

        Returns:
            BytesIO: A binary stream containing the generated PDF report.
        """
        buffer = BytesIO()
        # Page size is letter. 0.5 inch margins = 36 pt. Printable width = 540 pt.
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=54
        )
        story = []
        styles = getSampleStyleSheet()

        # Define custom premium styles matching the dashboard report layout
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=15
        )

        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.white
        )

        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#334155')
        )

        table_cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=table_cell_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0f172a')
        )

        kpi_val_style = ParagraphStyle(
            'KPIValue',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=18,
            textColor=colors.HexColor('#1e3a8a'),
            alignment=1 # Center
        )

        kpi_lbl_style = ParagraphStyle(
            'KPILabel',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#64748b'),
            alignment=1 # Center
        )

        # 1. Header Title Block
        story.append(Paragraph("IT STAFF PERFORMANCE REPORT", title_style))
        gen_time = datetime.now().strftime('%B %d, %Y %I:%M %p')
        story.append(Paragraph(f"Ticket-Tally IT Support Staff Metrics & bull; Generated on {gen_time}", subtitle_style))
        story.append(Spacer(1, 5))

        # 2. Staff KPI Summary Block
        total_staff = len(staff_list)
        total_active = 0
        total_resolved = 0
        csat_values = []
        for staff in staff_list:
            try:
                total_active += int(staff.get("active", 0))
            except (ValueError, TypeError):
                pass
            try:
                total_resolved += int(staff.get("resolved", 0))
            except (ValueError, TypeError):
                pass
            
            csat = staff.get("avg_csat")
            if isinstance(csat, (int, float)):
                csat_values.append(csat)
            elif str(csat).replace('.', '', 1).isdigit():
                csat_values.append(float(csat))

        avg_csat = round(sum(csat_values) / len(csat_values), 2) if csat_values else "N/A"
        avg_csat_str = f"{avg_csat:.1f}" if isinstance(avg_csat, (int, float)) else str(avg_csat)

        kpi_data = [
            [
                Paragraph(str(total_staff), kpi_val_style),
                Paragraph(str(total_active), kpi_val_style),
                Paragraph(str(total_resolved), kpi_val_style),
                Paragraph(avg_csat_str, kpi_val_style)
            ],
            [
                Paragraph("TOTAL AGENTS", kpi_lbl_style),
                Paragraph("ACTIVE TICKETS", kpi_lbl_style),
                Paragraph("RESOLVED TICKETS", kpi_lbl_style),
                Paragraph("AVERAGE CSAT RATING", kpi_lbl_style)
            ]
        ]

        # Total printable width is 540 pt
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 20))

        # 3. Staff Performance Table
        headers = [
            Paragraph("Agent Name", table_header_style),
            Paragraph("Email Address", table_header_style),
            Paragraph("Team", table_header_style),
            Paragraph("Active", table_header_style),
            Paragraph("Resolved", table_header_style),
            Paragraph("Avg CSAT", table_header_style),
            Paragraph("SLA Compliance", table_header_style)
        ]
        
        table_data = [headers]
        for staff in staff_list:
            csat_val = staff.get("avg_csat", "N/A")
            csat_str = f"{csat_val:.1f}" if isinstance(csat_val, (int, float)) else str(csat_val)
            
            table_data.append([
                Paragraph(staff.get("name", ""), table_cell_bold),
                Paragraph(staff.get("email", ""), table_cell_style),
                Paragraph(staff.get("team", "") or "Unassigned", table_cell_style),
                Paragraph(str(staff.get("active", 0)), table_cell_style),
                Paragraph(str(staff.get("resolved", 0)), table_cell_style),
                Paragraph(csat_str, table_cell_style),
                Paragraph(staff.get("sla_compliance", "100.0%"), table_cell_bold)
            ])

        # Widths summing to 540 pt
        t_perf = Table(table_data, colWidths=[100, 130, 90, 55, 55, 55, 55], repeatRows=1)
        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ]
        
        # Add alternating row background colors
        for idx in range(1, len(table_data)):
            if idx % 2 == 0:
                t_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f8fafc')))
                
        t_perf.setStyle(TableStyle(t_style))
        story.append(t_perf)

        # Build doc with NumberedCanvas to show footers
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_dashboard_performance_report(resolved_tickets, agent_data, category_data, summary_kpis):
        """Generates a highly polished, clean PDF performance report from dashboard data.

        Args:
            resolved_tickets (list): List of dicts representing ticket resolution times.
            agent_data (list): List of dicts representing agent performance metrics.
            category_data (list): List of dicts representing category performance metrics.
            summary_kpis (dict): Dict of summary KPI metrics.

        Returns:
            BytesIO: A binary stream containing the generated PDF report.
        """
        buffer = BytesIO()
        # Page size is letter (612 x 792 pt). 0.5 inch margins = 36 pt. Printable width = 540 pt.
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=54
        )
        
        story = []
        styles = getSampleStyleSheet()

        # Define custom premium styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=15
        )

        section_heading = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1e3a8a'),
            spaceBefore=16,
            spaceAfter=10,
            keepWithNext=True
        )

        table_header_style = ParagraphStyle(
            'TableHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            leading=11,
            textColor=colors.white
        )

        table_cell_style = ParagraphStyle(
            'TableCell',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#334155')
        )

        table_cell_bold = ParagraphStyle(
            'TableCellBold',
            parent=table_cell_style,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#0f172a')
        )

        kpi_val_style = ParagraphStyle(
            'KPIValue',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=18,
            textColor=colors.HexColor('#1e3a8a'),
            alignment=1 # Center
        )

        kpi_lbl_style = ParagraphStyle(
            'KPILabel',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#64748b'),
            alignment=1 # Center
        )

        # 1. Executive Title Header Block
        story.append(Paragraph("EXECUTIVE PERFORMANCE REPORT", title_style))
        gen_time = datetime.now().strftime('%B %d, %Y %I:%M %p')
        story.append(Paragraph(f"Ticket-Tally Support System &bull; Generated on {gen_time}", subtitle_style))
        story.append(Spacer(1, 5))

        # 2. Summary KPI Cards Block
        # We lay these out using a styled 2-row table (Row 1: values, Row 2: labels)
        kpi_data = [
            [
                Paragraph(str(summary_kpis.get("total_tickets", 0)), kpi_val_style),
                Paragraph(str(summary_kpis.get("resolved_count", 0)), kpi_val_style),
                Paragraph(f"{summary_kpis.get('avg_resolution_hours', 0.0):.1f} hrs" if isinstance(summary_kpis.get('avg_resolution_hours'), (int, float)) else str(summary_kpis.get('avg_resolution_hours', 'N/A')), kpi_val_style),
                Paragraph(f"{summary_kpis.get('breach_rate', 0.0):.1f}%" if isinstance(summary_kpis.get('breach_rate'), (int, float)) else str(summary_kpis.get('breach_rate', '0.0%')), kpi_val_style)
            ],
            [
                Paragraph("TOTAL TICKETS", kpi_lbl_style),
                Paragraph("RESOLVED TICKETS", kpi_lbl_style),
                Paragraph("AVG RESOLUTION TIME", kpi_lbl_style),
                Paragraph("SLA BREACH RATE", kpi_lbl_style)
            ]
        ]
        
        # Total printable width is 540 pt. Columns: 4 * 135 pt = 540 pt
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
            ('TOPPADDING', (0, 1), (-1, 1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 15))

        # 3. Section 1: Ticket Resolution Times
        story.append(Paragraph("1. Ticket Resolution Times", section_heading))
        
        if not resolved_tickets:
            story.append(Paragraph("No resolved or closed tickets found in this period.", table_cell_style))
            story.append(Spacer(1, 15))
        else:
            # Columns: ID (40pt), Title (170pt), Category (80pt), Priority (60pt), Assignee (100pt), Resolution Time (90pt)
            col_widths = [40, 170, 80, 60, 100, 90]
            
            headers = [
                Paragraph("ID", table_header_style),
                Paragraph("Ticket Title", table_header_style),
                Paragraph("Category", table_header_style),
                Paragraph("Priority", table_header_style),
                Paragraph("Assignee", table_header_style),
                Paragraph("Resolution Time", table_header_style)
            ]
            
            t1_data = [headers]
            for ticket in resolved_tickets:
                t1_data.append([
                    Paragraph(f"#{ticket.get('id')}", table_cell_bold),
                    Paragraph(ticket.get('title', ''), table_cell_style),
                    Paragraph(ticket.get('category', 'General'), table_cell_style),
                    Paragraph(ticket.get('priority', 'Medium'), table_cell_style),
                    Paragraph(ticket.get('assignee', 'Unassigned'), table_cell_style),
                    Paragraph(ticket.get('resolution_time_formatted', 'N/A'), table_cell_bold)
                ])
                
            t1 = Table(t1_data, colWidths=col_widths, repeatRows=1)
            t1_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ]
            
            # Alternating row background colors
            for idx in range(1, len(t1_data)):
                if idx % 2 == 0:
                    t1_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f8fafc')))
                    
            t1.setStyle(TableStyle(t1_style))
            story.append(t1)
            story.append(Spacer(1, 15))

        # 4. Section 2: Agent Performance Summary
        story.append(Paragraph("2. Ticket Volume and Breach Rates by IT Agent", section_heading))
        
        if not agent_data:
            story.append(Paragraph("No IT agents registered in the system.", table_cell_style))
            story.append(Spacer(1, 15))
        else:
            # Columns: Agent Name (110pt), Email (130pt), Team (80pt), Total (55pt), Active (55pt), Resolved (55pt), Breach Rate (55pt)
            col_widths = [110, 130, 80, 55, 55, 55, 55]
            
            headers = [
                Paragraph("Agent Name", table_header_style),
                Paragraph("Email", table_header_style),
                Paragraph("Team", table_header_style),
                Paragraph("Total", table_header_style),
                Paragraph("Active", table_header_style),
                Paragraph("Resolved", table_header_style),
                Paragraph("Breach Rate", table_header_style)
            ]
            
            t2_data = [headers]
            for agent in agent_data:
                t2_data.append([
                    Paragraph(agent.get('name', ''), table_cell_bold),
                    Paragraph(agent.get('email', ''), table_cell_style),
                    Paragraph(agent.get('team', 'Unassigned'), table_cell_style),
                    Paragraph(str(agent.get('total', 0)), table_cell_style),
                    Paragraph(str(agent.get('active', 0)), table_cell_style),
                    Paragraph(str(agent.get('resolved', 0)), table_cell_style),
                    Paragraph(agent.get('breach_rate', '0.0%'), table_cell_bold)
                ])
                
            t2 = Table(t2_data, colWidths=col_widths, repeatRows=1)
            t2_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ]
            
            for idx in range(1, len(t2_data)):
                if idx % 2 == 0:
                    t2_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f8fafc')))
                    
            t2.setStyle(TableStyle(t2_style))
            story.append(t2)
            story.append(Spacer(1, 15))

        # 5. Section 3: Performance Metrics by Category
        story.append(Paragraph("3. Category Performance Metrics", section_heading))
        
        if not category_data:
            story.append(Paragraph("No ticket category data found.", table_cell_style))
            story.append(Spacer(1, 15))
        else:
            # Columns: Category (140pt), Total (80pt), Active (80pt), Resolved (80pt), Avg Res. Time (80pt), Breach Rate (80pt)
            col_widths = [140, 80, 80, 80, 80, 80]
            
            headers = [
                Paragraph("Category", table_header_style),
                Paragraph("Total Tickets", table_header_style),
                Paragraph("Active Tickets", table_header_style),
                Paragraph("Resolved Tickets", table_header_style),
                Paragraph("Avg Res. Time", table_header_style),
                Paragraph("Breach Rate", table_header_style)
            ]
            
            t3_data = [headers]
            for cat in category_data:
                res_time_val = cat.get('avg_resolution_hours', 0.0)
                res_time_str = f"{res_time_val:.1f} hrs" if isinstance(res_time_val, (int, float)) and res_time_val > 0 else "N/A"
                
                t3_data.append([
                    Paragraph(cat.get('category', 'General'), table_cell_bold),
                    Paragraph(str(cat.get('total', 0)), table_cell_style),
                    Paragraph(str(cat.get('active', 0)), table_cell_style),
                    Paragraph(str(cat.get('resolved', 0)), table_cell_style),
                    Paragraph(res_time_str, table_cell_style),
                    Paragraph(cat.get('breach_rate', '0.0%'), table_cell_bold)
                ])
                
            t3 = Table(t3_data, colWidths=col_widths, repeatRows=1)
            t3_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ]
            
            for idx in range(1, len(t3_data)):
                if idx % 2 == 0:
                    t3_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f8fafc')))
                    
            t3.setStyle(TableStyle(t3_style))
            story.append(t3)

        # Build PDF using our custom NumberedCanvas to draw footer/page-numbers
        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer



class NumberedCanvas(canvas.Canvas):
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
            self.draw_page_number(num_pages)
            super().showPage()
        super().save()

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        # Thin divider line above footer
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        # Margin is 36pt (0.5 in), page width is 612pt
        self.line(36, 36, 576, 36)
        
        # Footer text
        self.drawString(36, 24, "Ticket-Tally — Executive Performance Report")
        self.drawRightString(576, 24, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

