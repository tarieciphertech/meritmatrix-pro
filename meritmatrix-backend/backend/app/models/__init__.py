"""
ORM model package. Import every model so Alembic and metadata-based tests see all tables.
"""
from app.models.associations import role_permissions, user_roles  # noqa: F401
from app.models.permission import Permission  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.school import School  # noqa: F401
from app.models.school_settings import SchoolSettings  # noqa: F401
from app.models.academic_year import AcademicYear  # noqa: F401
from app.models.term import Term  # noqa: F401
from app.models.clazz import Class  # noqa: F401
from app.models.subject import Subject  # noqa: F401
from app.models.class_subject import ClassSubject  # noqa: F401
from app.models.user_school import UserSchool  # noqa: F401
from app.models.student import Student, StudentStatus  # noqa: F401
from app.models.guardian import Guardian  # noqa: F401
from app.models.guardian_activation import GuardianActivation  # noqa: F401
from app.models.student_guardian import StudentGuardian, RelationshipType  # noqa: F401
from app.models.staff import Staff, EmploymentStatus  # noqa: F401
from app.models.enrollment import Enrollment, EnrollmentStatus  # noqa: F401
from app.models.calendar_event import CalendarEvent  # noqa: F401
from app.models.teaching_assignment import TeachingAssignment  # noqa: F401
from app.models.attendance_record import AttendanceRecord  # noqa: F401
from app.models.assessment import Assessment, AssessmentMark  # noqa: F401
from app.models.fee import FeeCharge, FeePayment  # noqa: F401
from app.models.grading_band import GradingBand  # noqa: F401

__all__ = [
    "User", "Role", "Permission", "RefreshToken", "user_roles", "role_permissions",
    "School", "SchoolSettings", "AcademicYear", "Term", "Class", "Subject", "ClassSubject", "UserSchool",
    "Student", "StudentStatus", "Guardian", "GuardianActivation", "StudentGuardian", "RelationshipType",
    "Staff", "EmploymentStatus", "Enrollment", "EnrollmentStatus", "CalendarEvent", "TeachingAssignment", "AttendanceRecord", "Assessment", "AssessmentMark", "FeeCharge", "FeePayment", "GradingBand",
]
