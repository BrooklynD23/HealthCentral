/**
 * /notifications now lives on the Reminders tab of the Medications page (UI-PG-MEDS, HC-UIMED-004).
 * The settings panel is components/medication-coach/RemindersPanel.tsx. This redirect keeps the medication the
 * user was looking at (medicationId) and keeps the old link working.
 */

import { Navigate, useSearchParams } from 'react-router-dom';

export function NotificationSettings() {
  const [searchParams] = useSearchParams();
  const target = new URLSearchParams({ tab: 'reminders' });
  const medicationId = searchParams.get('medicationId');
  if (medicationId) target.set('medicationId', medicationId);
  return <Navigate replace to={`/medications?${target.toString()}`} />;
}
