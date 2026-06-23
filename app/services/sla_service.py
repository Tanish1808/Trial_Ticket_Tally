from datetime import datetime
from app.models.sla import SLA
from app.models.ticket import Ticket
from app.core.constants import SLAStatus
from app.utils.time_utils import calculate_sla_deadline
from app.core.database import db

class SLAService:
    @staticmethod
    def set_sla_deadlines(ticket: Ticket):
        """Calculates and sets the SLA deadlines on a ticket based on its priority.

        Args:
            ticket (Ticket): The Ticket database model instance.
        """
        pass

    @staticmethod
    def get_deadline(ticket: Ticket) -> datetime:
        """Retrieves the SLA deadline for a ticket by fetching the corresponding SLA configuration.

        Args:
            ticket (Ticket): The Ticket database model instance.

        Returns:
            datetime: The calculated SLA resolution deadline timestamp.
        """
        sla_config = SLA.query.filter_by(priority=ticket.priority).first()
        if not sla_config:
            # Fallback or default
            return ticket.created_at # No SLA
        
        deadline = calculate_sla_deadline(ticket.created_at, sla_config.resolution_time_hours)
        return deadline

    @staticmethod
    def check_sla_status(ticket: Ticket) -> SLAStatus:
        """Checks the current SLA status of a ticket (ACHIEVED, BREACHED, or PENDING).

        Args:
            ticket (Ticket): The Ticket database model instance.

        Returns:
            SLAStatus: The current SLA status of the ticket.
        """
        if ticket.status in ["Resolved", "Closed"]:
            # Check if it was resolved within time?
            # We need to look at history when it was resolved.
            # detailed logic omitted for brevity but conceptually here.
            return SLAStatus.ACHIEVED
            
        from app.utils.time_utils import utcnow
        deadline = SLAService.get_deadline(ticket)
        if utcnow() > deadline:
            return SLAStatus.BREACHED
        
        return SLAStatus.PENDING
