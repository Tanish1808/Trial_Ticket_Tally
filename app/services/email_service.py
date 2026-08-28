import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from concurrent.futures import ThreadPoolExecutor
from app.core.config import Config
import logging

logger = logging.getLogger(__name__)

# Reusable executor for asynchronous background email sending
_email_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="EmailWorker")

class EmailService:
    @staticmethod
    def send_email_sync(to_email: str, subject: str, body: str, attachments=None, reply_to=None, sender_name=None):
        """Synchronously sends an HTML email with optional attachments and custom headers.

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

        if not to_email:
            logger.warning("Empty recipient email. Skipping email send.")
            return

        recipients_to_send = [to_email]

        for recipient in recipients_to_send:
            try:
                from email.mime.application import MIMEApplication
                msg = MIMEMultipart()
                
                if sender_name:
                    msg['From'] = f'"{sender_name}" <{Config.MAIL_USERNAME}>'
                else:
                    msg['From'] = Config.MAIL_USERNAME
                    
                msg['To'] = recipient
                msg['Subject'] = subject
                msg.attach(MIMEText(body, 'html'))
                
                if reply_to:
                    msg.add_header('Reply-To', reply_to)

                if attachments:
                    for filename, content in attachments:
                        part = MIMEApplication(content)
                        part.add_header('Content-Disposition', 'attachment', filename=filename)
                        msg.attach(part)

                server = smtplib.SMTP(Config.MAIL_SERVER, Config.MAIL_PORT, timeout=10)
                if Config.MAIL_USE_TLS:
                    server.starttls()
                
                server.login(Config.MAIL_USERNAME, Config.MAIL_PASSWORD)
                server.send_message(msg)
                server.quit()
                logger.info(f"Email sent successfully to {recipient}")
            except Exception as e:
                logger.error(f"Failed to send email to {recipient}: {e}", exc_info=True)

    @classmethod
    def send_email(cls, to_email: str, subject: str, body: str, attachments=None, reply_to=None, sender_name=None, sync: bool = False):
        """Sends an email asynchronously in a worker thread by default, avoiding request blocking.

        Args:
            to_email (str): The recipient's email address.
            subject (str): The subject line of the email.
            body (str): The HTML body of the email.
            attachments (list, optional): A list of tuples containing (filename, content) for attachments.
            reply_to (str, optional): A custom Reply-To email address.
            sender_name (str, optional): A custom display name for the sender.
            sync (bool, optional): If True, executes synchronously in the calling thread. Defaults to False.
        """
        is_testing = False
        try:
            from flask import current_app
            if current_app and current_app.config.get('TESTING'):
                is_testing = True
        except Exception:
            pass

        if sync or is_testing or getattr(Config, 'TESTING', False):
            cls.send_email_sync(to_email, subject, body, attachments=attachments, reply_to=reply_to, sender_name=sender_name)
        else:
            try:
                _email_executor.submit(
                    cls.send_email_sync,
                    to_email, subject, body, attachments, reply_to, sender_name
                )
            except Exception as e:
                logger.error(f"Failed to submit email task to background executor: {e}", exc_info=True)
                # Fallback to sync execution if executor submission fails
                cls.send_email_sync(to_email, subject, body, attachments=attachments, reply_to=reply_to, sender_name=sender_name)



