"""School-scoped fee charges, receipts and outstanding balances."""
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.academic_year import AcademicYear
from app.models.fee import FeeCharge, FeePayment
from app.models.student import Student
from app.models.term import Term
from app.models.user import User
from app.schemas.fee import FeeChargeCreate, FeeChargeResponse, FeePaymentCreate, FeePaymentResponse
from app.services.user_school_service import UserSchoolService
from app.services.audit_service import record_audit_event
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/fees", tags=["fees"])


def _school_access(db: Session, user: User, school_id: uuid.UUID) -> None:
    if SYSTEM_ADMIN_PERMISSION in _permission_names(user):
        return
    if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
        raise ForbiddenError("You do not have access to this school's fee records.", code="SCHOOL_ACCESS_DENIED")


def _charge_response(charge: FeeCharge):
    student = charge.student
    paid = sum((Decimal(str(p.amount)) for p in charge.payments), Decimal('0.00'))
    return {
        "id": charge.id, "school_id": charge.school_id, "student_id": charge.student_id,
        "student_number": student.student_number,
        "student_name": " ".join(x for x in [student.first_name, student.middle_name, student.last_name] if x),
        "academic_year_id": charge.academic_year_id, "academic_year_name": charge.academic_year.name,
        "term_id": charge.term_id, "term_name": charge.term.name if charge.term else None,
        "description": charge.description, "amount": float(charge.amount), "amount_paid": round(float(paid), 2),
        "balance": round(float(charge.amount - paid), 2), "due_date": charge.due_date,
        "is_void": charge.is_void, "notes": charge.notes, "created_at": charge.created_at,
    }


def _payment_response(payment: FeePayment):
    student = payment.student
    return {
        "id": payment.id, "school_id": payment.school_id, "student_id": payment.student_id,
        "student_number": student.student_number,
        "student_name": " ".join(x for x in [student.first_name, student.middle_name, student.last_name] if x),
        "charge_id": payment.charge_id, "charge_description": payment.charge.description,
        "payment_date": payment.payment_date, "amount": payment.amount, "method": payment.method,
        "reference": payment.reference, "notes": payment.notes, "created_at": payment.created_at,
    }


@router.get("/charges", response_model=list[FeeChargeResponse])
def list_charges(
    school_id: uuid.UUID = Query(...),
    student_id: Optional[uuid.UUID] = Query(default=None),
    include_void: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fees.read")),
):
    _school_access(db, current_user, school_id)
    query = db.query(FeeCharge).filter(FeeCharge.school_id == school_id)
    if student_id:
        query = query.filter(FeeCharge.student_id == student_id)
    if not include_void:
        query = query.filter(FeeCharge.is_void.is_(False))
    return [_charge_response(row) for row in query.order_by(FeeCharge.due_date.asc(), FeeCharge.created_at.desc()).all()]


@router.post("/charges", response_model=FeeChargeResponse, status_code=201)
def create_charge(
    payload: FeeChargeCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fees.create")),
):
    _school_access(db, current_user, school_id)
    student = db.query(Student).filter(Student.id == payload.student_id, Student.school_id == school_id, Student.is_active.is_(True)).first()
    year = db.query(AcademicYear).filter(AcademicYear.id == payload.academic_year_id, AcademicYear.school_id == school_id, AcademicYear.is_active.is_(True)).first()
    term = None
    if payload.term_id:
        term = db.query(Term).filter(Term.id == payload.term_id, Term.academic_year_id == payload.academic_year_id, Term.is_active.is_(True)).first()
    if not student or not year or (payload.term_id and not term):
        raise NotFoundError("Choose an active student, academic year and optional term from this school.", code="FEE_TARGET_NOT_FOUND")
    charge = FeeCharge(school_id=school_id, created_by_user_id=current_user.id, **payload.model_dump())
    db.add(charge)
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="fees.charge_created", entity_type="fee_charge",
        entity_id=charge.id,
        details={"student_id": str(student.id), "amount": str(payload.amount), "description": payload.description},
    )
    db.commit()
    db.refresh(charge)
    return _charge_response(charge)


@router.get("/payments", response_model=list[FeePaymentResponse])
def list_payments(
    school_id: uuid.UUID = Query(...),
    student_id: Optional[uuid.UUID] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fees.read")),
):
    _school_access(db, current_user, school_id)
    query = db.query(FeePayment).filter(FeePayment.school_id == school_id)
    if student_id:
        query = query.filter(FeePayment.student_id == student_id)
    return [_payment_response(row) for row in query.order_by(FeePayment.payment_date.desc(), FeePayment.created_at.desc()).all()]


@router.post("/payments", response_model=FeePaymentResponse, status_code=201)
def create_payment(
    payload: FeePaymentCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("fees.create")),
):
    _school_access(db, current_user, school_id)
    charge = db.query(FeeCharge).filter(FeeCharge.id == payload.charge_id, FeeCharge.school_id == school_id, FeeCharge.is_void.is_(False)).with_for_update().first()
    if not charge:
        raise NotFoundError("Outstanding fee charge not found in this school.", code="FEE_CHARGE_NOT_FOUND")
    paid = sum((Decimal(str(p.amount)) for p in charge.payments), Decimal('0.00'))
    remaining = Decimal(str(charge.amount)) - paid
    if payload.amount > remaining:
        raise ConflictError("Payment cannot exceed the remaining balance on this charge.", code="PAYMENT_EXCEEDS_BALANCE")
    payment = FeePayment(
        school_id=school_id, student_id=charge.student_id, recorded_by_user_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(payment)
    record_audit_event(
        db, school_id=school_id, actor_user_id=current_user.id,
        action="fees.payment_recorded", entity_type="fee_payment",
        entity_id=payment.id,
        details={
            "student_id": str(charge.student_id), "charge_id": str(charge.id),
            "amount": str(payload.amount), "payment_date": payload.payment_date.isoformat(),
            "method": payload.method,
        },
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("This payment reference already exists for the school.", code="DUPLICATE_PAYMENT_REFERENCE")
    db.refresh(payment)
    return _payment_response(payment)
