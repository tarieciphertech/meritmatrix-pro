import { useCallback, useEffect, useState, type FormEvent } from 'react';
import { api, ApiError } from '../lib/api';
import type {
  GuardianResponse,
  RelationshipType,
  StudentGuardianCreate,
  StudentGuardianResponse,
  StudentResponse,
} from '../types';
import { RELATIONSHIP_TYPES } from '../types';
import { Badge, Button, EmptyState, Field, Modal, Select, Spinner } from '../components/ui';

interface StudentGuardiansModalProps {
  student: StudentResponse | null;
  schoolId: string;
  onClose: () => void;
}

const relationshipLabels: Record<RelationshipType, string> = {
  mother: 'Mother',
  father: 'Father',
  guardian: 'Guardian',
  grandparent: 'Grandparent',
  sibling: 'Sibling',
  other: 'Other',
};

export default function StudentGuardiansModal({
  student,
  schoolId,
  onClose,
}: StudentGuardiansModalProps) {
  const [guardians, setGuardians] = useState<GuardianResponse[]>([]);
  const [relationships, setRelationships] = useState<StudentGuardianResponse[]>([]);
  const [guardianId, setGuardianId] = useState('');
  const [relationshipType, setRelationshipType] = useState<RelationshipType>('guardian');
  const [isPrimary, setIsPrimary] = useState(true);
  const [isEmergencyContact, setIsEmergencyContact] = useState(true);
  const [receivesNotifications, setReceivesNotifications] = useState(true);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!student) return;
    setLoading(true);
    setError(null);
    try {
      const [guardianList, relationshipList] = await Promise.all([
        api.get<GuardianResponse[]>('/api/v1/guardians', { school_id: schoolId, limit: 200 }),
        api.get<StudentGuardianResponse[]>(`/api/v1/student-guardians/student/${student.id}`),
      ]);
      setGuardians(guardianList.filter((guardian) => guardian.is_active));
      setRelationships(relationshipList);
      setGuardianId((current) => {
        if (current && guardianList.some((guardian) => guardian.id === current && guardian.is_active)) {
          return current;
        }
        return '';
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load guardian assignments.');
    } finally {
      setLoading(false);
    }
  }, [schoolId, student]);

  useEffect(() => {
    setGuardians([]);
    setRelationships([]);
    setGuardianId('');
    setRelationshipType('guardian');
    setIsPrimary(true);
    setIsEmergencyContact(true);
    setReceivesNotifications(true);
    if (student) void load();
  }, [student, load]);

  async function handleAssign(event: FormEvent) {
    event.preventDefault();
    if (!student || !guardianId) return;
    setSaving(true);
    setError(null);
    try {
      const payload: StudentGuardianCreate = {
        student_id: student.id,
        guardian_id: guardianId,
        relationship_type: relationshipType,
        is_primary: isPrimary,
        is_emergency_contact: isEmergencyContact,
        receives_notifications: receivesNotifications,
      };
      await api.post<StudentGuardianResponse>('/api/v1/student-guardians', payload);
      setGuardianId('');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not assign this guardian.');
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove(relationship: StudentGuardianResponse) {
    const guardian = guardians.find((item) => item.id === relationship.guardian_id);
    const name = guardian ? `${guardian.first_name} ${guardian.last_name}` : 'this guardian';
    if (!window.confirm(`Remove ${name} from this student?`)) return;
    setError(null);
    try {
      await api.delete<void>(`/api/v1/student-guardians/${relationship.id}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not remove this guardian.');
    }
  }

  if (!student) return null;

  const availableGuardians = guardians.filter(
    (guardian) => !relationships.some((relationship) => relationship.guardian_id === guardian.id),
  );

  return (
    <Modal
      open={!!student}
      title={`Guardians — ${student.first_name} ${student.last_name}`}
      onClose={onClose}
    >
      <div className="space-y-5">
        <p className="text-sm text-slate-600">
          Assign one or more guardians to this student. You can choose a primary guardian,
          mark emergency contacts, and control who receives notifications.
        </p>

        {error && (
          <div role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700 ring-1 ring-red-200">
            {error}
          </div>
        )}

        {loading ? (
          <Spinner label="Loading guardian assignments…" />
        ) : (
          <section className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-900">Assigned guardians</h3>
            {relationships.length === 0 ? (
              <EmptyState title="No guardians assigned yet" hint="Add a guardian using the form below." />
            ) : (
              <div className="space-y-2">
                {relationships.map((relationship) => {
                  const guardian = guardians.find((item) => item.id === relationship.guardian_id);
                  return (
                    <div key={relationship.id} className="flex items-start justify-between gap-3 rounded-md border border-slate-200 p-3">
                      <div className="min-w-0">
                        <p className="font-medium text-slate-900">
                          {guardian ? `${guardian.first_name} ${guardian.middle_name ? `${guardian.middle_name} ` : ''}${guardian.last_name}` : 'Guardian record unavailable'}
                        </p>
                        {guardian && <p className="text-sm text-slate-500">{guardian.phone}</p>}
                        <p className="mt-1 text-xs text-slate-500">
                          {relationshipLabels[relationship.relationship_type]}
                        </p>
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {relationship.is_primary && <Badge tone="indigo">Primary</Badge>}
                          {relationship.is_emergency_contact && <Badge tone="amber">Emergency contact</Badge>}
                          {relationship.receives_notifications && <Badge tone="green">Receives notifications</Badge>}
                        </div>
                      </div>
                      <Button
                        variant="danger"
                        className="shrink-0 !px-2 !py-1 text-xs"
                        onClick={() => void handleRemove(relationship)}
                      >
                        Remove
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        )}

        <form onSubmit={handleAssign} className="space-y-4 border-t border-slate-200 pt-4">
          <h3 className="text-sm font-semibold text-slate-900">Assign a guardian</h3>
          {guardians.length === 0 ? (
            <p className="text-sm text-slate-600">
              There are no active guardians for this school yet. Create a guardian in the Guardians section first.
            </p>
          ) : availableGuardians.length === 0 ? (
            <p className="text-sm text-slate-600">All active guardians are already assigned to this student.</p>
          ) : (
            <>
              <Field label="Guardian" required>
                <Select required value={guardianId} onChange={(event) => setGuardianId(event.target.value)}>
                  <option value="">Select a guardian…</option>
                  {availableGuardians.map((guardian) => (
                    <option key={guardian.id} value={guardian.id}>
                      {guardian.first_name} {guardian.middle_name ? `${guardian.middle_name} ` : ''}{guardian.last_name} — {guardian.phone}
                    </option>
                  ))}
                </Select>
              </Field>

              <Field label="Relationship to student" required>
                <Select
                  value={relationshipType}
                  onChange={(event) => setRelationshipType(event.target.value as RelationshipType)}
                >
                  {RELATIONSHIP_TYPES.map((type) => (
                    <option key={type} value={type}>{relationshipLabels[type]}</option>
                  ))}
                </Select>
              </Field>

              <div className="space-y-2">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={isPrimary} onChange={(event) => setIsPrimary(event.target.checked)} />
                  Primary guardian
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={isEmergencyContact} onChange={(event) => setIsEmergencyContact(event.target.checked)} />
                  Emergency contact
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input type="checkbox" checked={receivesNotifications} onChange={(event) => setReceivesNotifications(event.target.checked)} />
                  Receives school notifications
                </label>
              </div>
              <Button type="submit" disabled={saving || !guardianId}>
                {saving ? 'Assigning…' : 'Assign Guardian'}
              </Button>
            </>
          )}
        </form>

        <div className="flex justify-end border-t border-slate-200 pt-3">
          <Button variant="secondary" onClick={onClose}>Done</Button>
        </div>
      </div>
    </Modal>
  );
}
