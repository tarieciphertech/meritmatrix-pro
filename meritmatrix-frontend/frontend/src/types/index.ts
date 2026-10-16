// TypeScript types mirroring the backend Pydantic schemas.

export interface LoginRequest { email: string; password: string; }
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; expires_in: number; must_change_password?: boolean; }
export interface RoleResponse { id: string; name: string; description?: string | null; }
export interface UserResponse { id: string; email?: string | null; username?: string | null; first_name: string; last_name: string; is_active: boolean; is_verified: boolean; must_change_password?: boolean; last_login_at?: string | null; created_at: string; roles: RoleResponse[]; }

export type CountryCode = 'ZW' | 'BW';
export type InstitutionType = 'early_childhood' | 'primary' | 'secondary' | 'combined' | 'tertiary';
export const COUNTRY_CODES: CountryCode[] = ['ZW', 'BW'];
export const INSTITUTION_TYPES: { value: InstitutionType; label: string }[] = [
  { value: 'early_childhood', label: 'Early childhood / Kindergarten' },
  { value: 'primary', label: 'Primary school' },
  { value: 'secondary', label: 'Secondary school' },
  { value: 'combined', label: 'Combined school' },
  { value: 'tertiary', label: 'Tertiary / college' },
];
export interface SchoolResponse { id: string; name: string; code: string; registration_number?: string | null; address?: string | null; city?: string | null; country?: string | null; country_code?: CountryCode | null; institution_type?: InstitutionType | null; education_template_version?: number | null; phone?: string | null; email?: string | null; website?: string | null; logo_url?: string | null; timezone?: string | null; currency?: string | null; is_active: boolean; created_at: string; updated_at: string; }
export interface SchoolCreate { name: string; code: string; registration_number?: string | null; address?: string | null; city?: string | null; country?: string | null; country_code?: CountryCode | null; institution_type?: InstitutionType | null; education_template_version?: number | null; phone?: string | null; email?: string | null; website?: string | null; logo_url?: string | null; timezone?: string | null; currency?: string | null; }
export interface SchoolUpdate extends Partial<SchoolCreate> { is_active?: boolean; }

export interface AcademicYearResponse { id: string; school_id: string; name: string; start_date: string; end_date: string; is_current: boolean; is_active: boolean; created_at: string; updated_at: string; }
export interface AcademicYearCreate { name: string; start_date: string; end_date: string; }
export interface ClassResponse { id: string; school_id: string; name: string; code: string; level?: number | null; stream?: string | null; description?: string | null; is_active: boolean; created_at: string; updated_at: string; }
export interface ClassCreate { name: string; code: string; level?: number | null; stream?: string | null; description?: string | null; }
export type StudentStatus = 'active' | 'inactive' | 'graduated' | 'withdrawn' | 'transferred' | 'suspended';
export const STUDENT_STATUSES: StudentStatus[] = ['active','inactive','graduated','withdrawn','transferred','suspended'];
export interface StudentResponse { id: string; school_id: string; student_number: string; first_name: string; middle_name?: string | null; last_name: string; preferred_name?: string | null; date_of_birth?: string | null; gender?: string | null; nationality?: string | null; admission_date?: string | null; status: StudentStatus; email?: string | null; phone?: string | null; address?: string | null; emergency_contact_name?: string | null; emergency_contact_phone?: string | null; notes?: string | null; is_active: boolean; }
export interface StudentCreate { student_number: string; first_name: string; middle_name?: string | null; last_name: string; preferred_name?: string | null; date_of_birth?: string | null; gender?: string | null; nationality?: string | null; admission_date?: string | null; status?: StudentStatus; email?: string | null; phone?: string | null; address?: string | null; emergency_contact_name?: string | null; emergency_contact_phone?: string | null; notes?: string | null; }
export type StudentUpdate = Partial<Omit<StudentCreate, 'student_number'>> & { status?: StudentStatus };
export interface GuardianResponse { id: string; school_id: string; first_name: string; middle_name?: string | null; last_name: string; email?: string | null; phone: string; alternative_phone?: string | null; address?: string | null; occupation?: string | null; status: string; is_active: boolean; }
export interface GuardianCreate { first_name: string; middle_name?: string | null; last_name: string; email?: string | null; phone: string; alternative_phone?: string | null; address?: string | null; occupation?: string | null; }
export type GuardianUpdate = Partial<GuardianCreate>;
export type EmploymentStatus = 'active' | 'on_leave' | 'terminated' | 'retired' | 'contract_ended';
export const EMPLOYMENT_STATUSES: EmploymentStatus[] = ['active','on_leave','terminated','retired','contract_ended'];
export interface StaffResponse { id: string; school_id: string; user_id?: string | null; staff_number: string; first_name: string; middle_name?: string | null; last_name: string; email?: string | null; phone?: string | null; job_title?: string | null; employment_status: EmploymentStatus; hire_date?: string | null; termination_date?: string | null; notes?: string | null; is_active: boolean; }
export interface StaffCreate { staff_number: string; first_name: string; middle_name?: string | null; last_name: string; email?: string | null; phone?: string | null; job_title?: string | null; hire_date?: string | null; notes?: string | null; }
export type StaffUpdate = Partial<Omit<StaffCreate, 'staff_number'>> & { employment_status?: EmploymentStatus; termination_date?: string | null; };
export type EnrollmentStatus = 'active' | 'completed' | 'withdrawn' | 'transferred' | 'cancelled';
export const ENROLLMENT_STATUSES: EnrollmentStatus[] = ['active','completed','withdrawn','transferred','cancelled'];
export interface EnrollmentResponse { id: string; student_id: string; academic_year_id: string; class_id: string; enrollment_date?: string | null; withdrawal_date?: string | null; status: EnrollmentStatus; enrollment_number?: string | null; notes?: string | null; }
export interface EnrollmentCreate { student_id: string; academic_year_id: string; class_id: string; enrollment_date?: string | null; withdrawal_date?: string | null; status?: EnrollmentStatus; enrollment_number?: string | null; notes?: string | null; }
export interface EnrollmentUpdate { withdrawal_date?: string | null; status?: EnrollmentStatus; notes?: string | null; }
export type RelationshipType = 'mother' | 'father' | 'guardian' | 'grandparent' | 'sibling' | 'other';
export const RELATIONSHIP_TYPES: RelationshipType[] = ['mother','father','guardian','grandparent','sibling','other'];
export interface StudentGuardianResponse { id: string; student_id: string; guardian_id: string; relationship_type: RelationshipType; is_primary: boolean; is_emergency_contact: boolean; receives_notifications: boolean; }
export interface StudentGuardianCreate { student_id: string; guardian_id: string; relationship_type?: RelationshipType; is_primary?: boolean; is_emergency_contact?: boolean; receives_notifications?: boolean; }
export interface ApiErrorBody { error: { code: string; message: string; request_id?: string; }; }
export interface TermResponse { id: string; academic_year_id: string; name: string; term_number: number; start_date: string; end_date: string; is_current: boolean; is_active: boolean; created_at: string; updated_at: string; }
export interface SubjectResponse { id: string; school_id: string; name: string; code: string; description?: string | null; is_active: boolean; created_at: string; updated_at: string; }
export interface ClassSubjectResponse { id: string; class_id: string; subject_id: string; class_name?: string | null; class_code?: string | null; subject_name?: string | null; subject_code?: string | null; created_at: string; updated_at: string; }

export interface StaffAccountResponse { user_id: string; email: string; role: string; school_id: string; }
