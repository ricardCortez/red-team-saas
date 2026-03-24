"""Application Constants"""


class UserRole:
    ADMIN = "admin"
    MANAGER = "manager"
    PENTESTER = "pentester"
    VIEWER = "viewer"
    API_USER = "api_user"


VALID_ROLES = [
    UserRole.ADMIN,
    UserRole.MANAGER,
    UserRole.PENTESTER,
    UserRole.VIEWER,
    UserRole.API_USER,
]


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


VALID_TASK_STATUSES = [
    TaskStatus.PENDING,
    TaskStatus.RUNNING,
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
    TaskStatus.RETRYING,
]


class ErrorMessages:
    INVALID_CREDENTIALS = "Invalid credentials"
    USER_NOT_FOUND = "User not found"
    USER_ALREADY_EXISTS = "User already exists"
    UNAUTHORIZED = "Unauthorized"
    FORBIDDEN = "Forbidden"
    NOT_FOUND = "Not found"
    INVALID_INPUT = "Invalid input"
