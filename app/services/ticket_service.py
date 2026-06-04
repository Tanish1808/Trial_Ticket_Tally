from datetime import datetime
from app.core.database import db
from app.models.ticket import Ticket
from app.models.ticket_status_history import TicketStatusHistory
from app.schemas.ticket_schema import TicketCreate, TicketUpdate
from app.services.notification_service import NotificationService
from app.core.constants import TicketStatus
import logging

logger = logging.getLogger(__name__)

class TicketService:
    @staticmethod
    def create_ticket(data: TicketCreate, creator_id: int) -> Ticket:
        """Creates a new ticket, assigns it to a team, and triggers notifications.

        This method handles team assignment automatically based on the ticket category.
        If no team mapping is found, it defaults to 'IT Support'. It also records the
        initial status history and schedules notifications and email confirmations.

        Args:
            data (TicketCreate): The schema containing the ticket creation details.
            creator_id (int): The ID of the user creating the ticket.

        Returns:
            Ticket: The newly created ticket instance.
        """
        # Automatic Team Assignment
        from app.models.team import Team
        from app.models.team_mapping import TeamMapping

        # Self-healing auto-seed if mapping table is empty (e.g. test environment)
        try:
            if TeamMapping.query.count() == 0:
                default_mappings = {
                    'Software Issue': 'Software Team',
                    'Hardware Issue': 'Hardware Team',
                    'Network Issue': 'Network Team',
                    'Email Issue': 'IT Support'
                }
                for cat, team_name in default_mappings.items():
                    team = Team.query.filter_by(name=team_name).first()
                    if not team:
                        team = Team(name=team_name)
                        db.session.add(team)
                        db.session.commit()
                    mapping = TeamMapping(category=cat, team_id=team.id)
                    db.session.add(mapping)
                db.session.commit()
        except Exception as e:
            logger.warning(f"Failed to auto-seed team mappings: {e}")
            db.session.rollback()
        
        mapping = TeamMapping.query.filter_by(category=data.category).first()
        if mapping:
            team = mapping.team
        else:
            team = Team.query.filter_by(name='IT Support').first()
        
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
            logger.error(f"Failed to send ticket confirmation email: {e}")
        
        return new_ticket

    @staticmethod
    def get_ticket_by_id(ticket_id: int) -> Ticket:
        """Retrieves a ticket by its ID with all related relations eagerly loaded.

        Args:
            ticket_id (int): The ID of the ticket to retrieve.

        Returns:
            Ticket: The ticket instance, or None if not found.
        """
        from sqlalchemy.orm import joinedload, selectinload
        from app.models.comment import Comment
        
        return Ticket.query.options(
            joinedload(Ticket.creator),
            joinedload(Ticket.team),
            joinedload(Ticket.assignee),
            selectinload(Ticket.comments).joinedload(Comment.author),
            selectinload(Ticket.status_history).joinedload(TicketStatusHistory.changed_by)
        ).filter_by(id=ticket_id).first()

    @staticmethod
    def update_ticket(ticket_id: int, data: TicketUpdate, user_id: int) -> Ticket:
        """Updates a ticket's status, priority, category, or assignee.

        If the status is changed, a status history record is created and a status change
        notification is sent.

        Args:
            ticket_id (int): The ID of the ticket to update.
            data (TicketUpdate): The schema containing update values.
            user_id (int): The ID of the user performing the update.

        Returns:
            Ticket: The updated ticket instance.

        Raises:
            ValueError: If the ticket is not found or if the status of a closed ticket
                is modified.
        """
        ticket = Ticket.query.get(ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        
        updated = False
        old_status = ticket.status
        
        if data.status and data.status != ticket.status:
            if ticket.status == TicketStatus.CLOSED:
                raise ValueError("Cannot change the status of a closed ticket")
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
    def get_tickets(user, page=1, per_page=20):
        """Retrieves a paginated list of tickets tailored to the user's role and type.

        Demo users can only see demo tickets, while normal users can only see non-demo tickets.
        Employees see only their created tickets. IT Staff see tickets for their team or
        specifically assigned to them. Admins see all tickets (scoped by the demo filter).

        Args:
            user (User): The user requesting the tickets.
            page (int, optional): The page number for pagination. Defaults to 1.
            per_page (int, optional): The number of tickets per page. Defaults to 20.

        Returns:
            Pagination: A Flask-SQLAlchemy Pagination object containing the tickets.
        """
        from app.core.constants import UserRole
        from app.core.config import Config
        
        # Check if user is Demo User
        is_demo_user = (user.email == Config.DEMO_EMAIL)
        
        # Base query
        query = Ticket.query
        
        # FILTER: 
        # - Demo User sees ONLY Demo tickets
        # - Normal Users see ONLY Non-Demo tickets
        if is_demo_user:
            query = query.filter_by(is_demo=True)
        else:
            query = query.filter_by(is_demo=False)
        
        # Add a default sort (newest first) for consistent pagination
        query = query.order_by(Ticket.created_at.desc())
        
        if user.role == UserRole.EMPLOYEE:
             return query.filter_by(created_by_id=user.id).paginate(page=page, per_page=per_page, error_out=False)
             
        if user.role == UserRole.IT_STAFF:
            # IT Staff should see tickets for their team OR tickets specifically assigned to them
            if user.team_id:
                return query.filter(
                    (Ticket.team_id == user.team_id) | 
                    (Ticket.assigned_to_id == user.id)
                ).paginate(page=page, per_page=per_page, error_out=False)
            # If no team assigned, show all tickets (scoped by demo filter)
            return query.paginate(page=page, per_page=per_page, error_out=False)

        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def claim_ticket(ticket_id: int, user_id: int) -> Ticket:
        """Allows an IT staff member to claim a ticket for progression.

        Changes the status to IN_PROGRESS and assigns the ticket to the claiming user.
        Validates workload limits (max 3 active tickets), ticket existence, status, and
        potential concurrency issues. Sends an approach email to the ticket creator.

        Args:
            ticket_id (int): The ID of the ticket to claim.
            user_id (int): The ID of the IT staff member claiming the ticket.

        Returns:
            Ticket: The claimed and updated ticket instance.

        Raises:
            ValueError: If the ticket is not found, has been withdrawn, is already claimed/in progress,
                or if the user's active ticket workload limit has been reached.
        """
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
            logger.error(f"Failed to send approach email: {e}")

        return ticket

    @staticmethod
    def auto_close_resolved_tickets():
        """Automatically closes tickets that have been in 'Resolved' status for more than 7 days.

        Processes all tickets in batch. Records status history changes under the system account (None).
        """
        from datetime import datetime, timedelta
        from app.core.constants import TicketStatus
        from app.models.ticket import Ticket
        from app.core.database import db
        from app.models.ticket_status_history import TicketStatusHistory

        logger.info(f"[{datetime.utcnow()}] Starting auto-close check for Resolved tickets (7 days cutoff)...")
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        # Batch processing recommended for large datasets
        resolved_tickets = Ticket.query.filter(
            Ticket.status == TicketStatus.RESOLVED
        ).all()
        
        logger.info(f"Found {len(resolved_tickets)} tickets in Resolved status.")
        count = 0
        now = datetime.utcnow()
        for ticket in resolved_tickets:
            # Use updated_at if available, otherwise createdAt
            last_activity = ticket.updated_at if ticket.updated_at else ticket.created_at
            
            if last_activity <= cutoff_date:
                logger.info(f"Auto-closing Ticket #{ticket.id} (Last activity: {last_activity})")
                old_status = ticket.status
                ticket.status = TicketStatus.CLOSED
                ticket.updated_at = now
                
                # Add History - System Action
                history = TicketStatusHistory(
                    ticket_id=ticket.id,
                    old_status=old_status,
                    new_status=TicketStatus.CLOSED,
                    changed_by_id=None # System
                )
                db.session.add(history)
                count += 1
            else:
                logger.info(f"Skipping Ticket #{ticket.id} - too recent ({last_activity})")
            
        db.session.commit()
        logger.info(f"Auto-close task finished. Closed {count} tickets.")

