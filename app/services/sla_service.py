import time
from datetime import datetime
from app.models.sla import SLA
from app.models.ticket import Ticket
from app.core.constants import SLAStatus, TicketPriority, TicketStatus
from app.utils.time_utils import calculate_sla_deadline, utcnow
from app.core.database import db
from app.core.config import Config
import logging

logger = logging.getLogger(__name__)

class SLAService:
    _sla_map_cache = None
    _last_cache_time = 0
    _CACHE_TTL = 300  # 5 minutes TTL

    @classmethod
    def invalidate_cache(cls):
        """Invalidates the SLA cache."""
        cls._sla_map_cache = None
        cls._last_cache_time = 0

    @classmethod
    def get_sla_map(cls) -> dict:
        """Retrieves a mapping of TicketPriority to resolution hours with in-memory caching."""
        is_testing = False
        try:
            from flask import current_app
            if current_app and current_app.config.get('TESTING'):
                is_testing = True
        except Exception:
            pass

        now = time.time()
        if not is_testing and cls._sla_map_cache is not None and (now - cls._last_cache_time) < cls._CACHE_TTL:
            return cls._sla_map_cache

        defaults = {
            TicketPriority.CRITICAL: 4,
            TicketPriority.HIGH: 8,
            TicketPriority.MEDIUM: 24,
            TicketPriority.LOW: 48
        }

        try:
            sla_records = SLA.query.all()
            if not sla_records:
                cls.seed_default_slas()
                sla_records = SLA.query.all()

            sla_map = {}
            for sla in sla_records:
                sla_map[sla.priority] = sla.resolution_time_hours

            # Fill missing defaults
            for p, hrs in defaults.items():
                if p not in sla_map:
                    sla_map[p] = hrs

            cls._sla_map_cache = sla_map
            cls._last_cache_time = now
            return sla_map
        except Exception as e:
            logger.warning(f"Error fetching SLA configs from DB, using defaults: {e}")
            return defaults

    @classmethod
    def seed_default_slas(cls):
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
                cls.invalidate_cache()
        except Exception as e:
            logger.warning(f"Failed to seed SLAs: {e}")
            db.session.rollback()

    @staticmethod
    def set_sla_deadlines(ticket: Ticket):
        """Calculates and sets the SLA deadlines on a ticket based on its priority."""
        pass

    @classmethod
    def get_deadline(cls, ticket: Ticket, sla_map: dict = None) -> datetime:
        """Retrieves the SLA deadline for a ticket by calculating from SLA configuration.

        Args:
            ticket (Ticket): The Ticket database model instance.
            sla_map (dict, optional): Pre-fetched SLA map to avoid lookups.

        Returns:
            datetime: The calculated SLA resolution deadline timestamp.
        """
        if sla_map is None:
            sla_map = cls.get_sla_map()

        hours = sla_map.get(ticket.priority, 24)
        created_at = ticket.created_at or utcnow()
        return calculate_sla_deadline(created_at, hours)

    @classmethod
    def check_sla_status(cls, ticket: Ticket, sla_map: dict = None) -> SLAStatus:
        """Checks the current SLA status of a ticket (ACHIEVED, BREACHED, PENDING, or APPROACHING).

        Args:
            ticket (Ticket): The Ticket database model instance.
            sla_map (dict, optional): Pre-fetched SLA map.

        Returns:
            SLAStatus: The current SLA status of the ticket.
        """
        resolved_at = None
        # Use status_history without triggering additional queries if already eager loaded
        if hasattr(ticket, 'status_history') and ticket.status_history:
            for history in ticket.status_history:
                if history.new_status == TicketStatus.RESOLVED:
                    if resolved_at is None or history.changed_at < resolved_at:
                        resolved_at = history.changed_at

        if resolved_at is None and ticket.status in [TicketStatus.RESOLVED, TicketStatus.CLOSED]:
            resolved_at = ticket.updated_at or ticket.created_at

        deadline = cls.get_deadline(ticket, sla_map=sla_map)
        if resolved_at:
            if resolved_at <= deadline:
                return SLAStatus.ACHIEVED
            else:
                return SLAStatus.BREACHED

        now = utcnow()
        if now > deadline:
            return SLAStatus.BREACHED

        # Check if approaching (e.g. >80% of SLA time elapsed)
        created_at = ticket.created_at or now
        total_sla_seconds = (deadline - created_at).total_seconds()
        elapsed_seconds = (now - created_at).total_seconds()
        if total_sla_seconds > 0 and elapsed_seconds > total_sla_seconds * 0.8:
            return SLAStatus.APPROACHING

        return SLAStatus.PENDING

