import os
# from weasyprint import HTML # Uncomment when weasyprint is installed and needed
# For now, providing a placeholder or basic text generation to avoid heavy dependency issues 
# if GTK/etc aren't installed on the user environment.
# But the requirement asked for it. I will write the code but wrap in try/except or just assume it works.

def generate_ticket_pdf(ticket_data: dict) -> str:
    """
    Generates a PDF for the ticket and returns the file path.
    """
    try:
        from weasyprint import HTML
        html_content = f"""
        <h1>Ticket #{ticket_data['id']}</h1>
        <h2>{ticket_data['title']}</h2>
        <p><strong>Status:</strong> {ticket_data['status']}</p>
        <p><strong>Priority:</strong> {ticket_data['priority']}</p>
        <hr>
        <p>{ticket_data['description']}</p>
        """
        
        filename = f"ticket_{ticket_data['id']}.pdf"
        filepath = os.path.join(os.getcwd(), 'static', 'reports', filename)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        HTML(string=html_content).write_pdf(filepath)
        return filepath
    except ImportError:
        print("WeasyPrint not installed/configured.")
        return None
    except Exception as e:
        print(f"PDF Gen Error: {e}")
        return None
