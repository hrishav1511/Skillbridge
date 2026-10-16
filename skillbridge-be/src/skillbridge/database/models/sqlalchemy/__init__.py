from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .users import User
from .roles import Role
from .tutors import Tutor
from .students import Student
from .user_role_associations import UserRoleAssociation
from .chat_rooms import ChatRoom
from .chat_room_members import ChatRoomMember
from .chat_messages import ChatMessage
from .message_read_status import MessageReadStatus
from .services import Service
from .service_bookings import ServiceBooking
from .service_revisions import ServiceRevision
from .tutor_revisions import TutorRevision
from .tutor_reviews import TutorReview
from .service_reviews import ServiceReview
from .refresh_tokens import RefreshToken
from .notifications import Notification
from .service_attachments import ServiceAttachment
from .student_favorite_tutors import StudentFavoriteTutor
from .student_favorite_services import StudentFavoriteService
from .reported_tutors import ReportedTutor
from .reported_services import ReportedService
from .booking_reschedule_proposals import BookingRescheduleProposal
from .reported_reviews import ReportedReview
