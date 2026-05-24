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
      const newRecords = [record, ...prev].slice(0, 20); // Keep last 20
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
