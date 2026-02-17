from app.core.config import Config

def get_base_style():
    return """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f6f8; }
        .container { max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .header { background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%); padding: 30px 20px; text-align: center; color: white; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .content { padding: 30px; }
        .button { display: inline-block; padding: 12px 24px; background-color: #6366f1; color: white; text-decoration: none; border-radius: 6px; font-weight: 600; margin-top: 20px; }
        .footer { background-color: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }
        .info-box { background-color: #f1f5f9; border-left: 4px solid #6366f1; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .credential-label { font-weight: bold; color: #475569; display: block; margin-bottom: 5px; }
        .credential-value { font-family: 'Courier New', monospace; background: #e2e8f0; padding: 4px 8px; border-radius: 4px; color: #1e293b; }
    </style>
    """

def get_signup_email(name):
    base_url = Config.BASE_URL
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Welcome to Ticket Tally</title>
        {get_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to Ticket Tally!</h1>
            </div>
            <div class="content">
                <p>Hi {name},</p>
                <p>Thank you for joining <strong>Ticket Tally</strong>. We're excited to have you on board!</p>
                <p>You now have full access to our ticket management system. You can:</p>
                <ul>
                    <li>Create and track support tickets</li>
                    <li>Collaborate with your team</li>
                    <li>Stay updated with real-time notifications</li>
                </ul>
                <div style="text-align: center;">
                    <a href="{base_url}/dashboard/employee" class="button">Go to Dashboard</a>
                </div>
                <p style="margin-top: 30px;">If you have any questions, feel free to reply to this email.</p>
                <p>Best regards,<br>The Ticket Tally Team</p>
            </div>
            <div class="footer">
                &copy; 2026 Ticket Tally. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

def get_staff_welcome_email(name, email, password, team_name):
    base_url = Config.BASE_URL
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Welcome to the Team</title>
        {get_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Welcome to the IT Team!</h1>
            </div>
            <div class="content">
                <p>Hello {name},</p>
                <p>You have been added as an IT Staff member to the <strong>{team_name}</strong> in Ticket Tally.</p>
                <p>Here are your login credentials:</p>
                
                <div class="info-box">
                    <div style="margin-bottom: 10px;">
                        <span class="credential-label">Email:</span>
                        <span class="credential-value">{email}</span>
                    </div>
                    <div>
                        <span class="credential-label">Temporary Password:</span>
                        <span class="credential-value">{password}</span>
                    </div>
                </div>

                <p>Please log in and change your password immediately.</p>
                
                <div style="text-align: center;">
                    <a href="{base_url}/dashboard/it-staff" class="button">Login & Get Started</a>
                </div>
                
                <p>Best regards,<br>Ticket Tally Admin</p>
            </div>
            <div class="footer">
                &copy; 2026 Ticket Tally. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

def get_ticket_created_email(name, ticket_id, title):
    base_url = Config.BASE_URL
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Ticket Received</title>
        {get_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%);">
                <h1>Ticket Received</h1>
            </div>
            <div class="content">
                <p>Hello {name},</p>
                <p>We have received your ticket request. Our team will review it shortly.</p>
                
                <div class="info-box" style="border-left-color: #10b981;">
                    <div style="margin-bottom: 5px;">
                        <span class="credential-label">Ticket ID:</span>
                        <span style="font-size: 18px; font-weight: bold;">#{ticket_id}</span>
                    </div>
                    <div>
                        <span class="credential-label">Subject:</span>
                        <span>{title}</span>
                    </div>
                </div>

                <p>You will receive further updates via email.</p>
                
                <div style="text-align: center;">
                    <a href="{base_url}/ticket/{ticket_id}" class="button" style="background-color: #10b981;">View Ticket Status</a>
                </div>
                
                <p>Best regards,<br>Ticket Tally Support</p>
            </div>
            <div class="footer">
                &copy; 2026 Ticket Tally. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

def get_ticket_approached_email(name, ticket_id, title, approver_name):
    base_url = Config.BASE_URL
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Ticket Approached</title>
        {get_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);">
                <h1>Ticket Update</h1>
            </div>
            <div class="content">
                <p>Hello {name},</p>
                <p>Good news! Your ticket is now being handled.</p>
                
                <div class="info-box" style="border-left-color: #f59e0b;">
                    <div style="margin-bottom: 5px;">
                        <span class="credential-label">Ticket ID:</span>
                        <span style="font-size: 18px; font-weight: bold;">#{ticket_id}</span>
                    </div>
                    <div style="margin-bottom: 5px;">
                        <span class="credential-label">Subject:</span>
                        <span>{title}</span>
                    </div>
                    <div>
                        <span class="credential-label">Approached By:</span>
                        <span>{approver_name} (IT Staff)</span>
                    </div>
                </div>

                <p>An IT staff member has started working on your request. You will be notified when it is resolved.</p>
                
                <div style="text-align: center;">
                    <a href="{base_url}/ticket/{ticket_id}" class="button" style="background-color: #f59e0b;">View Ticket</a>
                </div>
                
                <p>Best regards,<br>Ticket Tally Support</p>
            </div>
            <div class="footer">
                &copy; 2026 Ticket Tally. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
def get_ticket_resolved_email(name, ticket_id, title):
    base_url = Config.BASE_URL
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Ticket Resolved</title>
        {get_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%);">
                <h1>Ticket Resolved</h1>
            </div>
            <div class="content">
                <p>Hello {name},</p>
                <p>Your ticket has been marked as <strong>Resolved</strong>. We hope we were able to assist you effectively.</p>
                
                <div class="info-box" style="border-left-color: #10b981;">
                    <div style="margin-bottom: 5px;">
                        <span class="credential-label">Ticket ID:</span>
                        <span style="font-size: 18px; font-weight: bold;">#{ticket_id}</span>
                    </div>
                    <div>
                        <span class="credential-label">Subject:</span>
                        <span>{title}</span>
                    </div>
                </div>

                <p>A PDF summary of your ticket is attached to this email for your records.</p>
                
                <div style="text-align: center;">
                    <a href="{base_url}/ticket/{ticket_id}" class="button" style="background-color: #10b981;">View Final Status</a>
                </div>
                
                <p>Best regards,<br>Ticket Tally Support</p>
            </div>
            <div class="footer">
                &copy; 2026 Ticket Tally. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """

def get_reset_password_email(name, reset_link):
    base_url = Config.BASE_URL
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reset Your Password</title>
        {get_base_style()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);">
                <h1>Password Reset</h1>
            </div>
            <div class="content">
                <p>Hello {name},</p>
                <p>We received a request to reset your password for your Ticket Tally account.</p>
                <p>If you didn't make this request, you can safely ignore this email.</p>
                
                <div style="text-align: center;">
                    <a href="{reset_link}" class="button" style="background-color: #ef4444;">Reset Password</a>
                </div>
                
                <p style="margin-top: 20px; font-size: 13px; color: #64748b;">
                    Or copy and paste this link into your browser:<br>
                    <a href="{reset_link}" style="color: #ef4444;">{reset_link}</a>
                </p>
                
                <p>This link will expire in 1 hour.</p>
                
                <p>Best regards,<br>Ticket Tally Security</p>
            </div>
            <div class="footer">
                &copy; 2026 Ticket Tally. All rights reserved.
            </div>
        </div>
    </body>
    </html>
    """
