// School context: loads the schools the current user can access and tracks
// the selected school. All school-scoped screens (students, guardians, staff,
// enrollments, classes, academic years) require a selected school because the
// backend mandates a school_id query parameter on those list endpoints.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { api } from './api';
import { useAuth } from './auth';
import type { SchoolResponse } from '../types';

const SELECTED_SCHOOL_KEY = 'meritmatrix.selectedSchoolId';

interface SchoolContextValue {
  schools: SchoolResponse[];
  loading: boolean;
  error: string | null;
  selectedSchool: SchoolResponse | null;
  selectSchool: (schoolId: string) => void;
  refresh: () => Promise<void>;
}

const SchoolContext = createContext<SchoolContextValue | null>(null);

export function SchoolProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [schools, setSchools] = useState<SchoolResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string | null>(
    () => localStorage.getItem(SELECTED_SCHOOL_KEY),
  );

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await api.get<SchoolResponse[]>('/api/v1/schools', { limit: 200 });
      setSchools(list);
    } catch (err) {
      setSchools([]);
      setError(err instanceof Error ? err.message : 'Failed to load schools');
    } finally {
      setLoading(false);
    }
  }, []);

  // Guardian users select only from linked schools inside the guardian portal.
  // The global school list is reserved for staff/admin users.
  useEffect(() => {
    const isGuardian = (user?.roles ?? []).some((role) => ['GUARDIAN', 'PARENT'].includes(role.name));
    if (user && !isGuardian) {
      void refresh();
    } else {
      setSchools([]);
      if (!user) {
        setSelectedSchoolId(null);
      }
    }
  }, [user, refresh]);

  // Persist selection; drop it if the user loses access to that school.
  useEffect(() => {
    if (!loading && selectedSchoolId && schools.length > 0) {
      if (!schools.some((s) => s.id === selectedSchoolId)) {
        setSelectedSchoolId(null);
        localStorage.removeItem(SELECTED_SCHOOL_KEY);
      }
    }
  }, [loading, schools, selectedSchoolId]);

  const selectSchool = useCallback((schoolId: string) => {
    setSelectedSchoolId(schoolId);
    localStorage.setItem(SELECTED_SCHOOL_KEY, schoolId);
  }, []);

  const selectedSchool = useMemo(
    () => schools.find((s) => s.id === selectedSchoolId) ?? null,
    [schools, selectedSchoolId],
  );

  const value = useMemo(
    () => ({ schools, loading, error, selectedSchool, selectSchool, refresh }),
    [schools, loading, error, selectedSchool, selectSchool, refresh],
  );

  return <SchoolContext.Provider value={value}>{children}</SchoolContext.Provider>;
}

export function useSchool(): SchoolContextValue {
  const ctx = useContext(SchoolContext);
  if (!ctx) throw new Error('useSchool must be used within SchoolProvider');
  return ctx;
}