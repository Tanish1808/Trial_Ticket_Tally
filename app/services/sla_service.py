from datetime import datetime
from app.models.sla import SLA
from app.models.ticket import Ticket
from app.core.constants import SLAStatus, TicketPriority, TicketStatus
from app.utils.time_utils import calculate_sla_deadline
from app.core.database import db

class SLAService:
    @staticmethod
    def seed_default_slas():
        """Seeds default SLAs if the table is empty."""
        try:
            if SLA.query.count() == 0:
                defaults = [
                    SLA(priority=TicketPriority.CRITICAL, response_time_hours=1, resolution_time_hours=4),
                    SLA(priority=TicketPriority.HIGH, response_time_hours=2, resolution_time_hours=8),
                    SLA(priority=TicketPriority.MEDIUM, response_time_hours=4, resolution_time_hours=24),
                    SLA(priority=TicketPriority.LOW, response_time_hours=8, resolution_time_hours=48),
                ]
                for item in defaults:
                    db.session.add(item)
                db.session.commit()
        except Exception as e:
            db.session.rollback()

    @staticmethod
    def set_sla_deadlines(ticket: Ticket):
        """Calculates and sets the SLA deadlines on a ticket based on its priority.

        Args:
            ticket (Ticket): The Ticket database model instance.
        """
        # Dynamic deadline is used, but we keep this method interface for compatibility
        pass

    @staticmethod
    def get_deadline(ticket: Ticket) -> datetime:
        """Retrieves the SLA deadline for a ticket by fetching the corresponding SLA configuration.

        Args:
            ticket (Ticket): The Ticket database model instance.

        Returns:
            datetime: The calculated SLA resolution deadline timestamp.
        """
        SLAService.seed_default_slas()
        sla_config = SLA.query.filter_by(priority=ticket.priority).first()
        if not sla_config:
            # Fallback values matching frontend if SLA configuration is missing
            defaults = {
                TicketPriority.CRITICAL: 4,
                TicketPriority.HIGH: 8,
                TicketPriority.MEDIUM: 24,
                TicketPriority.LOW: 48
            }
            hours = defaults.get(ticket.priority, 24)
        else:
            hours = sla_config.resolution_time_hours
            
        return calculate_sla_deadline(ticket.created_at, hours)

    @staticmethod
    def check_sla_status(ticket: Ticket) -> SLAStatus:
        """Checks the current SLA status of a ticket (ACHIEVED, BREACHED, PENDING, or APPROACHING).

        Args:
            ticket (Ticket): The Ticket database model instance.

        Returns:
            SLAStatus: The current SLA status of the ticket.
        """
        resolved_at = None
        # Eager load status history to find resolution time
        for history in ticket.status_history:
            if history.new_status == TicketStatus.RESOLVED:
                if resolved_at is None or history.changed_at < resolved_at:
                    resolved_at = history.changed_at
                    
        if resolved_at is None and ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            resolved_at = ticket.updated_at or ticket.created_at
            
        deadline = SLAService.get_deadline(ticket)
        if resolved_at:
            if resolved_at <= deadline:
                return SLAStatus.ACHIEVED
            else:
                return SLAStatus.BREACHED
                
        from app.utils.time_utils import utcnow
        now = utcnow()
        if now > deadline:
            return SLAStatus.BREACHED
            
        # Check if approaching (e.g. >80% of SLA time elapsed)
        total_sla_seconds = (deadline - ticket.created_at).total_seconds()
        elapsed_seconds = (now - ticket.created_at).total_seconds()
        if total_sla_seconds > 0 and elapsed_seconds > total_sla_seconds * 0.8:
            return SLAStatus.APPROACHING
            
        return SLAStatus.PENDING
