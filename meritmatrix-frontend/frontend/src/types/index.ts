// TypeScript types mirroring the backend Pydantic schemas.
// Source of truth: backend/app/schemas/*.py — keep these in sync.

// ---------- Auth ----------

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// ---------- Users / Roles ----------

export interface RoleResponse {
  id: string;
  name: string;
  description?: string | null;
}

export interface UserResponse {
  id: string;
  email: string;
  username?: string | null;
  first_name: string;
  last_name: string;
  is_active: boolean;
  is_verified: boolean;
  last_login_at?: string | null;
  created_at: string;
  roles: RoleResponse[];
}

// ---------- Schools ----------

export interface SchoolResponse {
  id: string;
  name: string;
  code: string;
  registration_number?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  logo_url?: string | null;
  timezone?: string | null;
  currency?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SchoolCreate {
  name: string;
  code: string;
  registration_number?: string | null;
  address?: string | null;
  city?: string | null;
  country?: string | null;
  phone?: string | null;
  email?: string | null;
  website?: string | null;
  logo_url?: string | null;
  timezone?: string | null;
  currency?: string | null;
}

export interface SchoolUpdate extends Partial<SchoolCreate> {
  is_active?: boolean;
}

// ---------- Academic Years ----------

export interface AcademicYearResponse {
  id: string;
  school_id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AcademicYearCreate {
  name: string;
  start_date: string;
  end_date: string;
}

// ---------- Classes ----------

export interface ClassResponse {
  id: string;
  school_id: string;
  name: string;
  code: string;
  level?: number | null;
  stream?: string | null;
  description?: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClassCreate {
  name: string;
  code: string;
  level?: number | null;
  stream?: string | null;
  description?: string | null;
}

// ---------- Students ----------

export type StudentStatus =
  | 'active'
  | 'inactive'
  | 'graduated'
  | 'withdrawn'
  | 'transferred'
  | 'suspended';

export const STUDENT_STATUSES: StudentStatus[] = [
  'active',
  'inactive',
  'graduated',
  'withdrawn',
  'transferred',
  'suspended',
];

export interface StudentResponse {
  id: string;
  school_id: string;
  student_number: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  preferred_name?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  nationality?: string | null;
  admission_date?: string | null;
  status: StudentStatus;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  notes?: string | null;
  is_active: boolean;
}

export interface StudentCreate {
  student_number: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  preferred_name?: string | null;
  date_of_birth?: string | null;
  gender?: string | null;
  nationality?: string | null;
  admission_date?: string | null;
  status?: StudentStatus;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  notes?: string | null;
}

export type StudentUpdate = Partial<Omit<StudentCreate, 'student_number'>> & {
  status?: StudentStatus;
};

// ---------- Guardians ----------

export interface GuardianResponse {
  id: string;
  school_id: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  email?: string | null;
  phone: string;
  alternative_phone?: string | null;
  address?: string | null;
  occupation?: string | null;
  status: string;
  is_active: boolean;
}

export interface GuardianCreate {
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  email?: string | null;
  phone: string;
  alternative_phone?: string | null;
  address?: string | null;
  occupation?: string | null;
}

export type GuardianUpdate = Partial<GuardianCreate>;

// ---------- Staff ----------

export type EmploymentStatus =
  | 'active'
  | 'on_leave'
  | 'terminated'
  | 'retired'
  | 'contract_ended';

export const EMPLOYMENT_STATUSES: EmploymentStatus[] = [
  'active',
  'on_leave',
  'terminated',
  'retired',
  'contract_ended',
];

export interface StaffResponse {
  id: string;
  school_id: string;
  staff_number: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  job_title?: string | null;
  employment_status: EmploymentStatus;
  hire_date?: string | null;
  termination_date?: string | null;
  notes?: string | null;
  is_active: boolean;
}

export interface StaffCreate {
  staff_number: string;
  first_name: string;
  middle_name?: string | null;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  job_title?: string | null;
  hire_date?: string | null;
  notes?: string | null;
}

export type StaffUpdate = Partial<Omit<StaffCreate, 'staff_number'>> & {
  employment_status?: EmploymentStatus;
  termination_date?: string | null;
};

// ---------- Enrollments ----------

export type EnrollmentStatus =
  | 'active'
  | 'completed'
  | 'withdrawn'
  | 'transferred'
  | 'cancelled';

export const ENROLLMENT_STATUSES: EnrollmentStatus[] = [
  'active',
  'completed',
  'withdrawn',
  'transferred',
  'cancelled',
];

export interface EnrollmentResponse {
  id: string;
  student_id: string;
  academic_year_id: string;
  class_id: string;
  enrollment_date?: string | null;
  withdrawal_date?: string | null;
  status: EnrollmentStatus;
  enrollment_number?: string | null;
  notes?: string | null;
}

export interface EnrollmentCreate {
  student_id: string;
  academic_year_id: string;
  class_id: string;
  enrollment_date?: string | null;
  withdrawal_date?: string | null;
  status?: EnrollmentStatus;
  enrollment_number?: string | null;
  notes?: string | null;
}

// Backend PATCH /api/v1/enrollments/{id} only accepts these fields
// (student/year/class/enrollment_date/enrollment_number are immutable).
export interface EnrollmentUpdate {
  withdrawal_date?: string | null;
  status?: EnrollmentStatus;
  notes?: string | null;
}

// ---------- Student-Guardian relationships ----------

export type RelationshipType =
  | 'mother'
  | 'father'
  | 'guardian'
  | 'grandparent'
  | 'sibling'
  | 'other';

export const RELATIONSHIP_TYPES: RelationshipType[] = [
  'mother',
  'father',
  'guardian',
  'grandparent',
  'sibling',
  'other',
];

export interface StudentGuardianResponse {
  id: string;
  student_id: string;
  guardian_id: string;
  relationship_type: RelationshipType;
  is_primary: boolean;
  is_emergency_contact: boolean;
  receives_notifications: boolean;
}

export interface StudentGuardianCreate {
  student_id: string;
  guardian_id: string;
  relationship_type?: RelationshipType;
  is_primary?: boolean;
  is_emergency_contact?: boolean;
  receives_notifications?: boolean;
}

// ---------- Errors ----------

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    request_id?: string;
  };
}