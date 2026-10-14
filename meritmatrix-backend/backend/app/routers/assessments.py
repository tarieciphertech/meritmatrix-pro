"""School-scoped assessment setup, mark entry and calculated results."""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.dependencies import SYSTEM_ADMIN_PERMISSION, _permission_names, require_permission
from app.database import get_db
from app.models.academic_year import AcademicYear
from app.models.assessment import Assessment, AssessmentMark
from app.models.class_subject import ClassSubject
from app.models.clazz import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.student import Student
from app.models.subject import Subject
from app.models.term import Term
from app.models.user import User
from app.schemas.assessment import AssessmentCreate, AssessmentResponse, AssessmentUpdate, MarkBatch, MarkResponse
from app.services.user_school_service import UserSchoolService
from app.utils.errors import ConflictError, ForbiddenError, NotFoundError

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])
results_router = APIRouter(prefix="/api/v1/results", tags=["academic-results"])


def _school_access(db: Session, user: User, school_id: uuid.UUID) -> None:
    if SYSTEM_ADMIN_PERMISSION in _permission_names(user):
        return
    if not UserSchoolService(db).is_user_member_of_school(user.id, school_id):
        raise ForbiddenError("You do not have access to this school's academic records.", code="SCHOOL_ACCESS_DENIED")


def _assessment_row(db: Session, assessment_id: uuid.UUID):
    row = (
        db.query(Assessment, Class, Subject, Term)
        .join(ClassSubject, ClassSubject.id == Assessment.class_subject_id)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .join(Term, Term.id == Assessment.term_id)
        .filter(Assessment.id == assessment_id)
        .first()
    )
    if not row:
        raise NotFoundError("Assessment not found.", code="ASSESSMENT_NOT_FOUND")
    assessment, clazz, subject, term = row
    return {
        "id": assessment.id, "school_id": assessment.school_id,
        "class_subject_id": assessment.class_subject_id, "term_id": assessment.term_id,
        "title": assessment.title, "assessment_type": assessment.assessment_type,
        "assessment_date": assessment.assessment_date, "max_score": assessment.max_score,
        "weight_percent": assessment.weight_percent, "is_published": assessment.is_published,
        "instructions": assessment.instructions, "class_name": clazz.name,
        "class_code": clazz.code, "subject_name": subject.name, "subject_code": subject.code,
        "term_name": term.name, "created_at": assessment.created_at, "updated_at": assessment.updated_at,
    }


def _mark_response(mark: AssessmentMark):
    enrollment = mark.enrollment
    student = enrollment.student
    assessment = mark.assessment
    return {
        "id": mark.id, "assessment_id": mark.assessment_id, "enrollment_id": mark.enrollment_id,
        "score": mark.score, "percentage": round(100 * mark.score / assessment.max_score, 2),
        "remarks": mark.remarks, "student_id": student.id, "student_number": student.student_number,
        "student_name": " ".join(x for x in [student.first_name, student.middle_name, student.last_name] if x),
        "created_at": mark.created_at, "updated_at": mark.updated_at,
    }


@router.get("", response_model=list[AssessmentResponse])
def list_assessments(
    school_id: uuid.UUID = Query(...),
    class_id: Optional[uuid.UUID] = Query(default=None),
    term_id: Optional[uuid.UUID] = Query(default=None),
    include_unpublished: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("assessments.read")),
):
    _school_access(db, current_user, school_id)
    query = db.query(Assessment.id).join(ClassSubject, ClassSubject.id == Assessment.class_subject_id).join(Class, Class.id == ClassSubject.class_id).filter(Assessment.school_id == school_id, Class.school_id == school_id)
    if class_id:
        query = query.filter(Class.id == class_id)
    if term_id:
        query = query.filter(Assessment.term_id == term_id)
    if not include_unpublished:
        query = query.filter(Assessment.is_published.is_(True))
    ids = [x[0] for x in query.order_by(Assessment.assessment_date.desc(), Assessment.title.asc()).all()]
    return [_assessment_row(db, x) for x in ids]


@router.post("", response_model=AssessmentResponse, status_code=201)
def create_assessment(
    payload: AssessmentCreate,
    school_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("assessments.create")),
):
    _school_access(db, current_user, school_id)
    pair = (
        db.query(ClassSubject, Class, Subject)
        .join(Class, Class.id == ClassSubject.class_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .filter(ClassSubject.id == payload.class_subject_id, Class.school_id == school_id, Subject.school_id == school_id, Class.is_active.is_(True), Subject.is_active.is_(True))
        .first()
    )
    term = db.query(Term).join(AcademicYear, AcademicYear.id == Term.academic_year_id).filter(Term.id == payload.term_id, Term.is_active.is_(True), AcademicYear.school_id == school_id, AcademicYear.is_active.is_(True)).first()
    if not pair or not term:
        raise NotFoundError("Choose a class subject and active term from the selected school.", code="ASSESSMENT_TARGET_NOT_FOUND")
    if payload.assessment_date and not (term.start_date <= payload.assessment_date <= term.end_date):
        raise ConflictError("Assessment date must fall within the selected term.", code="ASSESSMENT_DATE_OUTSIDE_TERM")
    assessment = Assessment(school_id=school_id, **payload.model_dump())
    db.add(assessment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("An assessment with this title already exists for this subject and term.", code="DUPLICATE_ASSESSMENT")
    db.refresh(assessment)
    return _assessment_row(db, assessment.id)


@router.patch("/{assessment_id}", response_model=AssessmentResponse)
def update_assessment(
    assessment_id: uuid.UUID,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("assessments.update")),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise NotFoundError("Assessment not found.", code="ASSESSMENT_NOT_FOUND")
    _school_access(db, current_user, assessment.school_id)
    changes = payload.model_dump(exclude_unset=True)
    if "max_score" in changes and changes["max_score"] is not None:
        if db.query(AssessmentMark).filter(AssessmentMark.assessment_id == assessment.id, AssessmentMark.score > changes["max_score"]).first():
            raise ConflictError("Maximum score cannot be reduced below an already-recorded mark.", code="MAX_SCORE_BELOW_EXISTING_MARKS")
    for field, value in changes.items():
        setattr(assessment, field, value)
    term = db.query(Term).filter(Term.id == assessment.term_id).first()
    if assessment.assessment_date and term and not (term.start_date <= assessment.assessment_date <= term.end_date):
        raise ConflictError("Assessment date must fall within the selected term.", code="ASSESSMENT_DATE_OUTSIDE_TERM")
    db.commit()
    db.refresh(assessment)
    return _assessment_row(db, assessment.id)


@router.get("/{assessment_id}/marks", response_model=list[MarkResponse])
def list_marks(
    assessment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("assessments.read")),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise NotFoundError("Assessment not found.", code="ASSESSMENT_NOT_FOUND")
    _school_access(db, current_user, assessment.school_id)
    rows = db.query(AssessmentMark).filter(AssessmentMark.assessment_id == assessment_id).join(Enrollment).join(Student).order_by(Student.last_name, Student.first_name).all()
    return [_mark_response(mark) for mark in rows]


@router.put("/{assessment_id}/marks", response_model=list[MarkResponse])
def save_marks(
    assessment_id: uuid.UUID,
    payload: MarkBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("assessments.create")),
):
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if not assessment:
        raise NotFoundError("Assessment not found.", code="ASSESSMENT_NOT_FOUND")
    _school_access(db, current_user, assessment.school_id)
    if assessment.is_published:
        raise ConflictError("Published assessments are locked. Unpublish it before editing marks.", code="ASSESSMENT_PUBLISHED")
    enrollment_ids = [mark.enrollment_id for mark in payload.marks]
    if len(set(enrollment_ids)) != len(enrollment_ids):
        raise ConflictError("Each student can appear only once in a marks submission.", code="DUPLICATE_STUDENT_MARK")
    class_subject = db.query(ClassSubject).filter(ClassSubject.id == assessment.class_subject_id).first()
    valid = {
        row.id: row for row in db.query(Enrollment)
        .join(AcademicYear, AcademicYear.id == Enrollment.academic_year_id)
        .join(Student, Student.id == Enrollment.student_id)
        .filter(Enrollment.id.in_(enrollment_ids), Enrollment.class_id == class_subject.class_id,
                Enrollment.status == EnrollmentStatus.ACTIVE, AcademicYear.school_id == assessment.school_id,
                AcademicYear.id == assessment.term.academic_year_id, Student.school_id == assessment.school_id,
                Student.is_active.is_(True)).all()
    }
    if len(valid) != len(enrollment_ids):
        raise ForbiddenError("Every mark must belong to an active student enrolled in this assessment's class and term.", code="MARK_ENROLLMENT_MISMATCH")
    if any(mark.score > assessment.max_score for mark in payload.marks):
        raise ConflictError("A mark cannot exceed the assessment's maximum score.", code="MARK_EXCEEDS_MAXIMUM")
    try:
        for entry in payload.marks:
            mark = db.query(AssessmentMark).filter(AssessmentMark.assessment_id == assessment_id, AssessmentMark.enrollment_id == entry.enrollment_id).first()
            if mark:
                mark.score, mark.remarks, mark.marked_by_user_id = entry.score, entry.remarks, current_user.id
            else:
                mark = AssessmentMark(assessment_id=assessment_id, enrollment_id=entry.enrollment_id, score=entry.score, remarks=entry.remarks, marked_by_user_id=current_user.id)
                db.add(mark)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Marks could not be saved because of a duplicate or conflicting record.", code="MARK_SAVE_CONFLICT")
    rows = db.query(AssessmentMark).filter(AssessmentMark.assessment_id == assessment_id).join(Enrollment).join(Student).order_by(Student.last_name, Student.first_name).all()
    return [_mark_response(mark) for mark in rows]


@results_router.get("", response_model=list[dict])
def list_results(
    school_id: uuid.UUID = Query(...),
    class_id: Optional[uuid.UUID] = Query(default=None),
    term_id: Optional[uuid.UUID] = Query(default=None),
    student_id: Optional[uuid.UUID] = Query(default=None),
    include_unpublished: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("assessments.read")),
):
    _school_access(db, current_user, school_id)
    query = (
        db.query(AssessmentMark, Assessment, Enrollment, Student, ClassSubject, Subject, Term)
        .join(Assessment, Assessment.id == AssessmentMark.assessment_id)
        .join(Enrollment, Enrollment.id == AssessmentMark.enrollment_id)
        .join(Student, Student.id == Enrollment.student_id)
        .join(ClassSubject, ClassSubject.id == Assessment.class_subject_id)
        .join(Subject, Subject.id == ClassSubject.subject_id)
        .join(Term, Term.id == Assessment.term_id)
        .filter(Assessment.school_id == school_id, Student.school_id == school_id)
    )
    if not include_unpublished:
        query = query.filter(Assessment.is_published.is_(True))
    if class_id:
        query = query.filter(Enrollment.class_id == class_id)
    if term_id:
        query = query.filter(Assessment.term_id == term_id)
    if student_id:
        query = query.filter(Student.id == student_id)
    rows = query.order_by(Student.last_name, Student.first_name, Subject.name, Term.term_number, Assessment.assessment_date).all()
    grouped = {}
    for mark, assessment, enrollment, student, class_subject, subject, term in rows:
        key = (str(student.id), str(enrollment.class_id), str(subject.id), str(term.id))
        item = grouped.setdefault(key, {
            "student_id": student.id, "student_number": student.student_number,
            "student_name": " ".join(x for x in [student.first_name, student.middle_name, student.last_name] if x),
            "class_id": enrollment.class_id, "class_name": enrollment.class_.name,
            "subject_id": subject.id, "subject_name": subject.name, "term_id": term.id,
            "term_name": term.name, "assessments": [], "weighted_sum": 0.0,
            "weight_total": 0.0, "marks_recorded": 0, "assessments_count": 0,
        })
        percentage = round(100 * mark.score / assessment.max_score, 2)
        item["assessments"].append({
            "assessment_id": str(assessment.id), "title": assessment.title,
            "type": assessment.assessment_type, "score": mark.score,
            "max_score": assessment.max_score, "percentage": percentage,
            "weight_percent": assessment.weight_percent, "remarks": mark.remarks,
            "date": assessment.assessment_date.isoformat() if assessment.assessment_date else None,
        })
        item["weighted_sum"] += percentage * assessment.weight_percent
        item["weight_total"] += assessment.weight_percent
        item["marks_recorded"] += 1
        item["assessments_count"] += 1
    result = []
    for item in grouped.values():
        item["weighted_percentage"] = round(item.pop("weighted_sum") / item.pop("weight_total"), 2) if item["weight_total"] else None
        result.append(item)
    return result
