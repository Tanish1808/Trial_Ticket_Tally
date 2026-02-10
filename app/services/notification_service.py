from app.core.database import db
from app.models.notification import Notification
from app.core.extensions import socketio
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    @staticmethod
    def create_notification(user_id, title, message, type='info'):
        """Create a new notification and emit socket event"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            type=type,
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()

        # Emit socket event to the specific user room or just broadcast if simple
        # For scalable apps, we'd emit to room `user_{user_id}`
        # For now, let's emit 'new_notification' with data including user_id, 
        # and client will filter or we rely on socket rooms if set up.
        # Looking at ticket_socket.py, it's very basic.
        # Let's emit a global event and client checks ID, or better, emit to a room.
        # We need to ensure client joins room on connect.
        
        notification_data = notification.to_dict()
        socketio.emit('new_notification', notification_data)
        
        return notification

    @staticmethod
    def get_notifications(user_id, limit=20, unread_only=False):
        """Get notifications for a user"""
        query = Notification.query.filter_by(user_id=user_id)
        if unread_only:
            query = query.filter_by(is_read=False)
        
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_unread_count(user_id):
        """Get count of unread notifications"""
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()

    @staticmethod
    def mark_as_read(notification_id, user_id):
        """Mark a notification as read"""
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read(user_id):
        """Mark all notifications as read for a user"""
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()

    @staticmethod
    def clear_all_notifications(user_id):
        """Delete all notifications for a user"""
        Notification.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    # --- Event Helpers ---

    @staticmethod
    def notify_ticket_created(ticket, creator):
        """Notify Admins and IT Staff about a new ticket"""
        from app.models.user import User
        from app.core.constants import UserRole

        # Notify Creator
        NotificationService.create_notification(
            user_id=creator.id,
            title="Ticket Created Successfully",
            message=f"Your ticket #{ticket.id} '{ticket.title}' has been received.",
            type='success'
        )

        # Notify All Admins
        admins = User.query.filter_by(role=UserRole.ADMIN).all()
        for admin in admins:
            NotificationService.create_notification(
                user_id=admin.id,
                title="New Ticket Created",
                message=f"Ticket #{ticket.id}: {ticket.title} was created by {creator.full_name}",
                type='info'
            )

        # Notify IT Staff (All or Team specific?)
        # For simplicity, notify all IT staff for now, or those in the team if assigned
        if ticket.team_id:
            # Notify members of the team
            # We don't have a direct 'team.members' relationship easily accessible maybe?
            # Let's query users with that team_id
            staff_members = User.query.filter_by(role=UserRole.IT_STAFF, team_id=ticket.team_id).all()
        else:
            staff_members = User.query.filter_by(role=UserRole.IT_STAFF).all()

        for staff in staff_members:
             NotificationService.create_notification(
                user_id=staff.id,
                title="New Ticket Assigned to Team",
                message=f"Ticket #{ticket.id}: {ticket.title} is waiting for action.",
                type='info'
            )

    @staticmethod
    def notify_status_change(ticket, old_status, new_status):
        """Notify the ticket creator about status change"""
        from app.core.constants import TicketStatus
        from app.services.email_service import EmailService
        from app.services.email_templates import get_ticket_resolved_email
        from app.services.ticket_pdf_service import TicketPdfService

        # 1. Internal Notification
        NotificationService.create_notification(
            user_id=ticket.created_by_id,
            title="Ticket Status Updated",
            message=f"Your ticket #{ticket.id} '{ticket.title}' is now {new_status}.",
            type='success' if new_status == TicketStatus.RESOLVED else 'info'
        )

        # 2. Email Notification if Resolved
        # Use .value or string comparison to be safe against Enum variations
        status_val = str(new_status.value if hasattr(new_status, 'value') else new_status)
        
        if status_val == TicketStatus.RESOLVED.value:
            try:
                # 3. Generate PDF
                pdf_content = TicketPdfService.generate_ticket_pdf(ticket)
                
                # 4. Prepare and Send Email
                creator_name = ticket.creator.full_name if ticket.creator else "User"
                creator_email = ticket.creator.email if ticket.creator else None
                
                if creator_email:
                    email_body = get_ticket_resolved_email(
                        creator_name,
                        ticket.id,
                        ticket.title
                    )
                    
                    EmailService.send_email(
                        to_email=creator_email,
                        subject=f"Resolved: Ticket #{ticket.id} - {ticket.title}",
                        body=email_body,
                        attachments=[(f"Ticket_{ticket.id}_Summary.pdf", pdf_content)]
                    )
                else:
                    logger.warning(f"Could not send resolution email for ticket {ticket.id}: No creator email.")
            except Exception as e:
                logger.error(f"Failed to send resolution email for ticket {ticket.id}: {e}", exc_info=True)


    @staticmethod
    def notify_new_comment(ticket, comment, commenter):
        """Notify relevant parties about a new comment"""
        # If commenter is Ticket Creator -> Notify Assignee (if any) and Team
        # If commenter is Staff -> Notify Creator
        
        recipients = set()
        
        # Notify Creator (if they didn't write the comment)
        if ticket.created_by_id != commenter.id:
            recipients.add(ticket.created_by_id)
            
        # Notify Assignee (if they didn't write it)
        if ticket.assigned_to_id and ticket.assigned_to_id != commenter.id:
            recipients.add(ticket.assigned_to_id)
            
        # If no assignee, but assigned to team, maybe notify team? (Too noisy maybe, let's stick to specific people)
        
        for user_id in recipients:
            NotificationService.create_notification(
                user_id=user_id,
                title=f"New Comment on Ticket #{ticket.id}",
                message=f"{commenter.full_name} commented: {comment.text[:50]}...",
                type='info'
            )

    @staticmethod
    def notify_password_reset(user, token):
        """Notify user about password reset request (Mock for internally generated notif, usually email)"""
        # In reality this should send an EMAIL. 
        # But if we also want an in-app notif (weird if they can't login, but maybe they are logged in?)
        # The AuthService calls this. 
        # Given the user can't login if they forgot password, this notification is only useful 
        # if they recover access or for security audit. 
        # Let's just create it.
        NotificationService.create_notification(
            user_id=user.id,
            title="Password Reset Requested",
            message="A password reset was requested for your account.",
            type='warning'
        )

