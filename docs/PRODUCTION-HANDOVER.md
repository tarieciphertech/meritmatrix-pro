# MeritMatrix Pro — Production Handover Pack

**Audience:** School management, designated school administrator, and authorised teachers  
**Application:** MeritMatrix Pro 2.0  
**Web application:** https://meritmatrix.cyphertech.co.zw/  
**API health:** https://meritmatrix-api.cyphertech.co.zw/health  
**API documentation (technical users):** https://meritmatrix-api.cyphertech.co.zw/api/v1/docs

## 1. Purpose and handover boundary

This document is the operational checklist for transferring day-to-day use of MeritMatrix Pro to school management. It is not a claim that every workflow has already passed school acceptance. The school administrator and nominated users must complete the checks in this document before entering live records at scale.

The application includes school-scoped areas for school configuration, staff, students, guardians, enrollments, teaching assignments, attendance, academic setup, assessments/results, fees/payments, report cards, and audit history. The exact features visible to each person depend on their assigned role and school access.

## 2. First access and account security

1. Open the web application using the URL above.
2. Sign in with the individual account issued by the authorised platform/school administrator.
3. If prompted to change a temporary password, set a unique password immediately.
4. Never share accounts between staff members. Never send passwords in a group chat or include them in this document.
5. Confirm the displayed name, role, and selected school before opening or editing records.
6. Sign out when using a shared computer. Keep devices and browsers protected with their own login controls.
7. Report a lost device, suspected password disclosure, unexpected access, or unfamiliar account immediately to the designated system contact.

**Account register (complete offline and store securely; do not add passwords):**

| Staff member | Login identifier | Assigned role | School | Account verified | Password changed |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

## 3. School administrator start-up sequence

Complete these items in order, using approved school information:

- [ ] Confirm the correct school is selected.
- [ ] Review school name, contact details, address, and branding.
- [ ] Confirm the academic year and term before entering current-year records.
- [ ] Review classes, subjects, and any school-specific academic configuration.
- [ ] Create or verify staff accounts and assign only the roles they need.
- [ ] Confirm each teacher's teaching assignments.
- [ ] Confirm student and guardian records and the school's approved identifiers.
- [ ] Agree the process for new admissions/enrollments and record corrections.
- [ ] Confirm the person authorised to enter, verify, and reconcile fee payments.
- [ ] Confirm who may publish results and report cards.

Do not guess missing student identifiers, dates of birth, guardian contacts, marks, balances, or payment references. Resolve discrepancies against the school's authoritative records.

## 4. Teacher daily workflow

1. Sign in using the teacher's own account.
2. Confirm the correct school, class, subject, and assigned teaching responsibilities.
3. Open the attendance area and select the correct date and class.
4. Mark attendance only from the school's verified register.
5. Save the register and confirm the saved state before leaving the page.
6. Report incorrect class assignments, duplicate students, or missing students to the school administrator; do not work around access restrictions by using another person's account.
7. Enter assessment marks only when authorised and according to the school's approved assessment rules.
8. Check that student names and class context are correct before saving or publishing any academic information.

## 5. Fees and payment controls

- Record only payments actually received and supported by the school's accepted evidence.
- Verify the student identity, amount, currency, date, payment method, and transaction/reference number before saving.
- Do not mark a payment as received merely because a parent says it has been sent.
- Reconcile application balances and receipts against the school's cashbook/bank/mobile-money statements.
- Corrections and reversals must be performed only by an authorised person and documented according to school policy.
- Never store card PINs, mobile-money PINs, banking passwords, or other payment credentials in MeritMatrix notes or general records.

## 6. Results and report cards

Before publishing results:

- [ ] Confirm the correct academic year, term, class, subject, and assessment.
- [ ] Confirm marks against signed/approved source records.
- [ ] Confirm grading bands and weighting rules with school management.
- [ ] Have a second authorised person review a sample of calculations.
- [ ] Generate a sample report card and check student identity, subjects, marks, grades, totals, and layout.
- [ ] Obtain management approval before publishing results or distributing report cards.

Do not publish unverified marks or use a report card as the sole source for correcting the underlying student record.

## 7. Data protection and school operating rules

- Use real student data only after school management confirms the account list, role permissions, and data-entry process.
- Restrict access to authorised staff and use the minimum permissions required for each job.
- Do not export, photograph, or forward student records unless the school has authorised the purpose and recipient.
- Keep printed registers and reports secure; collect them from shared printers promptly.
- Do not use production student information for demonstrations or testing.
- Use the application's available audit history when investigating changes; record the issue and notify the designated administrator.
- The school must nominate a person responsible for approving corrections to student records and another or the same authorised person for financial reconciliation.

## 8. Backup and recovery

A database backup was created before the latest backend release on 23 November 2026:

`/opt/meritmatrix/backups/meritmatrix-20261123-185933.dump`

The archive was checked with `pg_restore --list` and was readable. This confirms archive readability only; it does **not** prove that a full restore has been rehearsed.

Before the school begins substantial live data entry:

- [ ] The technical operator creates a fresh database backup.
- [ ] The operator verifies that the archive can be listed/read.
- [ ] The backup is stored with restricted permissions and retained separately from the running database.
- [ ] The school and technical operator agree who may request a restore and how the school will be notified.
- [ ] A restore rehearsal is scheduled in an isolated environment; never test a restore over the live production database.

Do not delete the database volume, run development seed scripts, or perform destructive migrations as part of routine handover.

## 9. Acceptance test record

Record the result of each test using a dedicated, approved test account and non-production test records where possible. If a test cannot be performed safely before handover, mark it **Not tested** and agree an owner and deadline rather than marking it passed.

| Test | Result (Pass / Fail / Not tested) | Tested by | Notes / issue reference |
|---|---|---|---|
| Administrator login and school selection |  |  |  |
| Teacher login and role restrictions |  |  |  |
| School profile and branding |  |  |  |
| Academic year, term, classes, subjects |  |  |  |
| Staff accounts and teaching assignments |  |  |  |
| Student and guardian record lookup |  |  |  |
| Attendance save and retrieval |  |  |  |
| Assessment entry and result calculation |  |  |  |
| Report-card preview/print |  |  |  |
| Fee entry, receipt, and reconciliation |  |  |  |
| Mobile browser access |  |  |  |
| School-to-school access isolation (where applicable) |  |  |  |
| Latest database backup verified |  |  |  |

## 10. Known handover cautions

- A successful code deployment or frontend build is not equivalent to end-to-end acceptance of every school workflow.
- The backup noted above has not had a full restore rehearsal.
- Notification functionality should not be promised unless separately demonstrated and accepted.
- Any failed or untested critical workflow must be written into the handover record with an owner and agreed resolution time.
- Do not load bulk live data until management has approved the data format, responsible operators, and correction process.

## 11. Support and escalation

The school should nominate one primary administrator to collect issues from teachers and guardians. Each report should include:

- Date/time and affected school.
- User role (never the password).
- Page or workflow affected.
- What the user expected and what happened.
- Student or transaction reference only through an approved secure channel.
- Screenshot with unrelated student/personal information hidden where possible.

For suspected unauthorised access or exposure of student/financial data, stop the affected activity and escalate immediately to the designated technical contact and school management.

## 12. Handover sign-off

**School representative:** ______________________________  
**Role:** ______________________________________________  
**Date/time:** _________________________________________  

**Technical representative:** ___________________________  
**Role:** ______________________________________________  
**Date/time:** _________________________________________  

**Outstanding issues / agreed follow-up:**  
__________________________________________________________________  
__________________________________________________________________  

**Acceptance status:**  
- [ ] Accepted for operational use
- [ ] Accepted with listed limitations and follow-up owners
- [ ] Not accepted — critical issue(s) remain

A signature confirms the scope and limitations recorded above; it does not certify that an untested workflow has passed.
