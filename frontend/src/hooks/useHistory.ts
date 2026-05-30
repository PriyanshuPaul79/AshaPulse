import { useState, useEffect } from 'react';
import { DiagnosisRecord, CriticalityLevel } from '../types/nidaan';

export function useHistory() {
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);

  useEffect(() => {
    const stored = localStorage.getItem('nidaan_history');
    if (stored) {
      try {
        setRecords(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse history", e);
      }
    }
  }, []);

  const addRecord = (record: DiagnosisRecord) => {
  setRecords(prev => {
    // Skip if same symptoms were saved within the last 60 seconds
    const isDuplicate = prev.some(r =>
      r.symptoms === record.symptoms &&
      Math.abs(new Date(r.timestamp).getTime() - new Date(record.timestamp).getTime()) < 60_000
    );
    if (isDuplicate) return prev;

    const newRecords = [record, ...prev].slice(0, 20);
    localStorage.setItem('nidaan_history', JSON.stringify(newRecords));
    return newRecords;
  });
};

  const clearAll = () => {
    localStorage.removeItem('nidaan_history');
    setRecords([]);
  };

  return { records, addRecord, clearAll };
}
