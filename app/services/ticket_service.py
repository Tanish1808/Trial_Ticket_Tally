from datetime import datetime
from app.core.database import db
from app.models.ticket import Ticket
from app.models.ticket_status_history import TicketStatusHistory
from app.schemas.ticket_schema import TicketCreate, TicketUpdate
from app.services.notification_service import NotificationService
from app.core.constants import TicketStatus

class TicketService:
    @staticmethod
    def create_ticket(data: TicketCreate, creator_id: int) -> Ticket:
        # Automatic Team Assignment
        from app.models.team import Team
        
        team_mapping = {
            'Software Issue': 'Software Team',
            'Hardware Issue': 'Hardware Team',
            'Network Issue': 'Network Team',
            'Email Issue': 'IT Support'
        }
        
        target_team_name = team_mapping.get(data.category, 'IT Support')
        team = Team.query.filter_by(name=target_team_name).first()
        
        new_ticket = Ticket(
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            created_by_id=creator_id,
            team_id=team.id if team else None
        )
        db.session.add(new_ticket)
        db.session.flush() # Get ID
        
        # Initial History
        history = TicketStatusHistory(
            ticket_id=new_ticket.id,
            old_status=None,
            new_status=new_ticket.status,
            changed_by_id=creator_id
        )
        db.session.add(history)
        db.session.commit()
        
        # Notify
        NotificationService.notify_ticket_created(new_ticket, new_ticket.creator)

        # Send Email Confirmation to Creator
        try:
            from app.services.email_service import EmailService
            from app.services.email_templates import get_ticket_created_email
            
            email_body = get_ticket_created_email(
                name=new_ticket.creator.full_name,
                ticket_id=new_ticket.id,
                title=new_ticket.title
            )
            
            EmailService.send_email(
                new_ticket.creator.email,
                f"Ticket Received - #{new_ticket.id} 🎫",
                email_body
            )
        except Exception as e:
            print(f"Failed to send ticket confirmation email: {e}")
        
        return new_ticket

    @staticmethod
    def get_ticket_by_id(ticket_id: int) -> Ticket:
        return Ticket.query.get(ticket_id)

    @staticmethod
    def update_ticket(ticket_id: int, data: TicketUpdate, user_id: int) -> Ticket:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        
        updated = False
        old_status = ticket.status
        
        if data.status and data.status != ticket.status:
            ticket.status = data.status
            # Add History
            history = TicketStatusHistory(
                ticket_id=ticket.id,
                old_status=old_status,
                new_status=data.status,
                changed_by_id=user_id
            )
            db.session.add(history)
            updated = True
            
        if data.priority:
            ticket.priority = data.priority
            updated = True

        if data.category:
            ticket.category = data.category
            updated = True
            
        if data.assigned_to_id:
            ticket.assigned_to_id = data.assigned_to_id
            updated = True
        
        if updated:
            ticket.updated_at = datetime.utcnow()
            db.session.commit()
            if old_status != ticket.status:
                 NotificationService.notify_status_change(ticket, old_status, ticket.status)
        
        return ticket

    @staticmethod
    def get_tickets(user):
        from app.core.constants import UserRole
        
        if user.role == UserRole.EMPLOYEE:
             return Ticket.query.filter_by(created_by_id=user.id).all()
             
        if user.role == UserRole.IT_STAFF:
            # IT Staff should see tickets for their team OR tickets specifically assigned to them
            if user.team_id:
                return Ticket.query.filter(
                    (Ticket.team_id == user.team_id) | 
                    (Ticket.assigned_to_id == user.id)
                ).all()
            # If no team assigned, show all tickets
            return Ticket.query.all()

        return Ticket.query.all()

    @staticmethod
    def claim_ticket(ticket_id: int, user_id: int) -> Ticket:
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")

        # Status Check
        if ticket.status == TicketStatus.WITHDRAWN:
            raise ValueError("Ticket has been withdrawn")

        # Concurrency Check
        if ticket.status in [TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED] or ticket.assigned_to_id is not None:
             raise ValueError("Ticket already in progress or claimed by another member")

        # Workload Check
        active_tickets_count = Ticket.query.filter_by(
            assigned_to_id=user_id,
            status=TicketStatus.IN_PROGRESS
        ).count()
        
        if active_tickets_count >= 3:
            raise ValueError("Workload limit reached. You cannot claim more than 3 tickets.")

        # Claim Ticket
        old_status = ticket.status
        ticket.assigned_to_id = user_id
        ticket.status = TicketStatus.IN_PROGRESS
        ticket.updated_at = datetime.utcnow()
        
        # History
        history = TicketStatusHistory(
            ticket_id=ticket.id,
            old_status=old_status,
            new_status=ticket.status,
            changed_by_id=user_id
        )
        db.session.add(history)
        db.session.commit()
        
        NotificationService.notify_status_change(ticket, old_status, ticket.status)
        
        # Send Email Notification to Creator
        try:
            from app.services.email_service import EmailService
            from app.services.email_templates import get_ticket_approached_email
            
            email_body = get_ticket_approached_email(
                name=ticket.creator.full_name,
                ticket_id=ticket.id,
                title=ticket.title,
                approver_name=ticket.assignee.full_name
            )
            
            EmailService.send_email(
                ticket.creator.email,
                f"Ticket Approached - #{ticket.id} 🚀",
                email_body
            )
        except Exception as e:
            print(f"Failed to send approach email: {e}")

        return ticket
