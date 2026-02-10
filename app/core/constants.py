from enum import Enum

class UserRole(str, Enum):
    EMPLOYEE = "employee"
    IT_STAFF = "it_staff"
    ADMIN = "admin"

class TicketStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"
    CLOSED = "Closed"
    WITHDRAWN = "Withdrawn"

class TicketPriority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class SLAStatus(str, Enum):
    PENDING = "Pending"
    ACHIEVED = "Achieved"

class ProjectStatus(str, Enum):
    PLANNING = "Planning"
    ACTIVE = "Active"
    ON_HOLD = "On Hold"
    COMPLETED = "Completed"
