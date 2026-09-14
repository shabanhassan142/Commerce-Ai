"""app/models/__init__.py — Central model registry."""

from app.models.user import User, UserRole
from app.models.customer import Customer
from app.models.address import Address
from app.models.category import Category
from app.models.seller import Seller
from app.models.product import Product, ProductImage
from app.models.order import Order, OrderItem, OrderStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.return_model import Return, ReturnReason, ReturnStatus
from app.models.ticket import (
    SupportTicket,
    TicketPriority,
    TicketStatus,
    SLA_HOURS,
    PRIORITY_SORT_WEIGHT,
    VALID_STATUS_TRANSITIONS,
)
from app.models.conversation import Conversation, AgentLog, MessageRole

# Module 5 models
from app.support.models.note import TicketNote
from app.support.models.reply import TicketReply, ReplyAuthorType
from app.timeline.models import TicketTimelineEvent, TimelineEventType
from app.audit.models import AuditLog
from app.notifications.models import Notification, NotificationEventType, NotificationChannel

__all__ = [
    "User", "UserRole",
    "Customer",
    "Address",
    "Category",
    "Seller",
    "Product", "ProductImage",
    "Order", "OrderItem", "OrderStatus",
    "Payment", "PaymentMethod", "PaymentStatus",
    "Return", "ReturnReason", "ReturnStatus",
    "SupportTicket", "TicketPriority", "TicketStatus",
    "SLA_HOURS", "PRIORITY_SORT_WEIGHT", "VALID_STATUS_TRANSITIONS",
    "Conversation", "AgentLog", "MessageRole",
    "TicketNote", "TicketReply", "ReplyAuthorType",
    "TicketTimelineEvent", "TimelineEventType",
    "AuditLog",
    "Notification", "NotificationEventType", "NotificationChannel",
]
