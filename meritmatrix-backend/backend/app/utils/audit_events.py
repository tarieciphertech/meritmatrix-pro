"""
Audit event identifiers.

These constants define the vocabulary the future audit-log system will
use. Milestone 2 only defines them for reuse by the auth service; actual
persistence of audit records is implemented in a later milestone.
"""


class AuditEvent:
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    TOKEN_REFRESH = "TOKEN_REFRESH"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
