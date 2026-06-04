import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import Config
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str, attachments=None, reply_to=None, sender_name=None):
        """Sends an HTML email with optional attachments and custom headers.

        Args:
            to_email (str): The recipient's email address.
            subject (str): The subject line of the email.
            body (str): The HTML body of the email.
            attachments (list, optional): A list of tuples containing (filename, content) for attachments.
            reply_to (str, optional): A custom Reply-To email address.
            sender_name (str, optional): A custom display name for the sender.
        """
        if not Config.MAIL_SERVER or not Config.MAIL_USERNAME:
            logger.warning("Email configuration missing. Skipping email send.")
            logger.info(f"Would have sent email to {to_email}: {subject}")
            return

        try:
            from email.mime.application import MIMEApplication
            msg = MIMEMultipart()
            
            if sender_name:
                # Format: "Sender Name" <system@email.com>
                msg['From'] = f'"{sender_name}" <{Config.MAIL_USERNAME}>'
            else:
                msg['From'] = Config.MAIL_USERNAME
                
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            if reply_to:
                msg.add_header('Reply-To', reply_to)

            if attachments:
                for filename, content in attachments:
                    part = MIMEApplication(content)
                    part.add_header('Content-Disposition', 'attachment', filename=filename)
                    msg.attach(part)

            server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT)
            if Config.MAIL_USE_TLS:
                server.starttls()
            
            server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            logger.info(f"Email sent to {to_email}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

