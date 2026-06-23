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
        
        assigned_to_id = None
        if hasattr(data, 'assigned_to_id') and data.assigned_to_id:
            from app.models.user import User, UserRole
            agent = User.query.filter_by(id=data.assigned_to_id).first()
            if agent and agent.role in [UserRole.IT_STAFF, UserRole.ADMIN]:
                assigned_to_id = agent.id
                if agent.team_id:
                    team = agent.team

        new_ticket = Ticket(
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            created_by_id=creator_id,
            team_id=team.id if team else None,
            assigned_to_id=assigned_to_id
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

        # Broadcast live activity
        NotificationService.broadcast_live_activity(
            category="created",
            ticket_id=new_ticket.id,
            message=f"New Ticket T-{1000 + new_ticket.id} ('{new_ticket.title}') was created by {new_ticket.creator.full_name}.",
            created_by=new_ticket.creator.full_name
        )

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
        ticket = db.session.get(Ticket, ticket_id)
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
            from app.models.user import User
            updater = db.session.get(User, user_id)
            updater_name = updater.full_name if updater else "System"

            ticket.updated_at = datetime.utcnow()
            db.session.commit()

            if old_status != ticket.status:
                NotificationService.notify_status_change(ticket, old_status, ticket.status)
                # Broadcast live activity status change
                old_status_val = old_status.value if hasattr(old_status, 'value') else str(old_status)
                new_status_val = ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status)
                NotificationService.broadcast_live_activity(
                    category="status_change",
                    ticket_id=ticket.id,
                    message=f"Ticket T-{1000 + ticket.id} status changed from '{old_status_val}' to '{new_status_val}' by {updater_name}.",
                    created_by=updater_name
                )
            if data.priority:
                priority_val = data.priority.value if hasattr(data.priority, 'value') else str(data.priority)
                NotificationService.broadcast_live_activity(
                    category="priority_change",
                    ticket_id=ticket.id,
                    message=f"Ticket T-{1000 + ticket.id} priority updated to '{priority_val}' by {updater_name}.",
                    created_by=updater_name
                )
            if data.assigned_to_id:
                assignee = db.session.get(User, data.assigned_to_id)
                assignee_name = assignee.full_name if assignee else "Unassigned"
                NotificationService.broadcast_live_activity(
                    category="assigned",
                    ticket_id=ticket.id,
                    message=f"Ticket T-{1000 + ticket.id} assigned to {assignee_name} by {updater_name}.",
                    created_by=updater_name
                )
        
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
        ticket = db.session.get(Ticket, ticket_id)
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
        
        # Broadcast live activity
        NotificationService.broadcast_live_activity(
            category="claimed",
            ticket_id=ticket.id,
            message=f"Ticket T-{1000 + ticket.id} ('{ticket.title}') was claimed by {ticket.assignee.full_name}.",
            created_by=ticket.assignee.full_name
        )
        
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

    @staticmethod
    def archive_and_purge_old_tickets() -> int:
        """Archives and permanently purges tickets older than the configured retention period.

        Tickets in terminal states (CLOSED or WITHDRAWN) or soft-deleted (is_deleted=True)
        that have not been updated since the cutoff date are serialized to JSON files in the
        configured archive folder, and then permanently deleted from the database along with
        their comments and status history.

        Returns:
            int: The number of tickets archived and purged.
        """
        import os
        import json
        from datetime import datetime, timedelta
        from flask import current_app
        from app.core.database import db
        from app.models.ticket import Ticket
        from app.core.constants import TicketStatus

        retention_days = current_app.config.get('RETENTION_DAYS', 365)
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        archive_dir = current_app.config.get('ARCHIVE_FOLDER', os.path.join(os.getcwd(), 'archive'))

        logger.info(f"[{datetime.utcnow()}] Starting data retention purge (cutoff date: {cutoff_date}, retention: {retention_days} days)...")

        # Ensure archive directory exists
        os.makedirs(archive_dir, exist_ok=True)

        # Query all tickets matching terminal states or soft-deleted, and updated_at <= cutoff_date
        query = Ticket.query.execution_options(include_deleted=True).filter(
            (Ticket.status.in_([TicketStatus.CLOSED, TicketStatus.WITHDRAWN])) | (Ticket.is_deleted == True)
        ).filter(
            Ticket.updated_at <= cutoff_date
        )
        old_tickets = query.all()

        logger.info(f"Found {len(old_tickets)} tickets eligible for archiving and purging.")
        count = 0
        for ticket in old_tickets:
            # Construct dictionary
            archive_data = {
                "id": ticket.id,
                "title": ticket.title,
                "description": ticket.description,
                "category": ticket.category,
                "status": ticket.status.value if hasattr(ticket.status, 'value') else str(ticket.status),
                "priority": ticket.priority.value if hasattr(ticket.priority, 'value') else str(ticket.priority),
                "is_demo": ticket.is_demo,
                "created_by_id": ticket.created_by_id,
                "assigned_to_id": ticket.assigned_to_id,
                "team_id": ticket.team_id,
                "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
                "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
                "is_deleted": ticket.is_deleted,
                "deleted_at": ticket.deleted_at.isoformat() if ticket.deleted_at else None,
                "comments": [
                    {
                        "id": comment.id,
                        "text": comment.text,
                        "user_id": comment.user_id,
                        "author_name": comment.author.full_name if comment.author else "Unknown",
                        "created_at": comment.created_at.isoformat() if comment.created_at else None
                    }
                    for comment in ticket.comments
                ],
                "status_history": [
                    {
                        "id": h.id,
                        "old_status": h.old_status.value if (h.old_status and hasattr(h.old_status, 'value')) else str(h.old_status) if h.old_status else None,
                        "new_status": h.new_status.value if hasattr(h.new_status, 'value') else str(h.new_status),
                        "changed_by_id": h.changed_by_id,
                        "changed_at": h.changed_at.isoformat() if h.changed_at else None
                    }
                    for h in ticket.status_history
                ]
            }

            archive_file_path = os.path.join(archive_dir, f"ticket_archive_{ticket.id}.json")
            try:
                with open(archive_file_path, 'w', encoding='utf-8') as f:
                    json.dump(archive_data, f, indent=4)
                
                db.session.delete(ticket)
                count += 1
            except Exception as e:
                logger.error(f"Failed to archive ticket #{ticket.id}: {e}")
                db.session.rollback()
                raise e

        if count > 0:
            db.session.commit()
            logger.info(f"Successfully archived and purged {count} tickets.")
        else:
            logger.info("No tickets met the retention criteria for purging.")

        return count

