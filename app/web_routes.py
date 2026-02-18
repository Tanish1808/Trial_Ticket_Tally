from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from app.services.email_service import EmailService

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    return render_template('index.html')

@web_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Validation
        if not name or not email or not message:
            flash('Please fill in all fields.', 'danger')
            return render_template('contact.html')
            
        # Save to Database
        try:
            from app.models.message import Message
            from app.core.database import db
            
            new_msg = Message(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            db.session.add(new_msg)
            db.session.commit()
            flash('Your message has been saved successfully! We will get back to you soon.', 'success')
            
        except Exception as db_err:
            print(f"Database Error: {db_err}")
            flash('Failed to save message. Please try again later.', 'danger')
            return render_template('contact.html')

        # Send Email to System AND Admin
        try:
            from app.models.user import User, UserRole
            from app.services.email_templates import get_contact_form_email
            
            # 1. Get System Email
            system_email = current_app.config.get('MAIL_USERNAME')
            
            # 2. Get Admin Email(s) from Database
            # assuming there is at least one admin, or get all
            admin_users = User.query.filter_by(role=UserRole.ADMIN).all()
            admin_emails = [u.email for u in admin_users]
            
            # Combine unique recipients (System + Admins + Hardcoded)
            recipients = set()
            if system_email:
                recipients.add(system_email)
            for email in admin_emails:
                recipients.add(email)
            
            # Explicitly add user requested email
            recipients.add('a79321035@gmail.com')
                
            if recipients:
                html_body = get_contact_form_email(name, email, subject, message)
                
                # Send to each recipient
                for recipient in recipients:
                    print(f"Sending contact email to: {recipient}") # Debug log
                    EmailService.send_email(
                        to_email=recipient,
                        subject=f"Contact Form: {subject}",
                        body=html_body,
                        reply_to=email,  # Set Reply-To to the sender's email
                        sender_name=f"{name} ({email})" # Show "Name (email)" as the sender
                    )
            
        except Exception as e:
            print(f"Contact Form Email Error: {e}")
            # Do not rollback or flash error to user if DB save succeeded
            
        return redirect(url_for('web.contact'))

    return render_template('contact.html')

@web_bp.route('/privacy')
def privacy():
    return render_template('legal.html', title='Privacy Policy', page_type='privacy', date='October 24, 2026')

@web_bp.route('/terms')
def terms():
    return render_template('legal.html', title='Terms of Service', page_type='terms', date='October 24, 2026')

@web_bp.route('/security')
def security():
    return render_template('legal.html', title='Security', page_type='security', date='October 24, 2026')

@web_bp.route('/docs')
def docs():
    # Placeholder for Documentation - Redirect to Features for now or simple page
    # Let's simple redirect to contact for "Request Docs" or show a "Coming Soon"
    return render_template('legal.html', title='Documentation', page_type='terms', date='Coming Soon') # Reuse terms layout temporarily

@web_bp.route('/help')
def help_center():
    return redirect(url_for('web.contact'))

@web_bp.route('/login')
def login():
    return render_template('login.html')

@web_bp.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@web_bp.route('/reset-password/<token>')
def reset_password_page(token):
    return render_template('reset_password.html', token=token)


@web_bp.route('/signup')
def signup():
    return render_template('signup.html')

@web_bp.route('/dashboard/admin')
def admin_dashboard():
    return render_template('admin-dashboard.html')

@web_bp.route('/dashboard/employee')
def employee_dashboard():
    return render_template('employee-dashboard.html')

@web_bp.route('/dashboard/it-staff')
def itstaff_dashboard():
    return render_template('itstaff-dashboard.html')

@web_bp.route('/profile')
def profile():
    return render_template('profile.html')

@web_bp.route('/projects')
def projects():
    return render_template('projects.html')

@web_bp.route('/ticket/<int:ticket_id>')
def ticket_details(ticket_id):
    # Pass ID to template, JS will fetch details
    return render_template('ticket-details.html', ticket_id=ticket_id)
