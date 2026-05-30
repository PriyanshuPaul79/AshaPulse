import { useState, useEffect } from 'react';

// const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_BASE = "https://ashapulse-production-444b.up.railway.app";
export function useBackendStatus() {
  const [isOnline, setIsOnline] = useState(false);
  const [mode, setMode] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    
    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        const data = await res.json();
        if (isMounted) {
          setIsOnline(data.status === 'ok');
          setMode(data.mode);
        }
      } catch (err) {
        if (isMounted) {
          setIsOnline(false);
          setMode(null);
        }
      }
    };

    checkStatus();
    const interval = setInterval(checkStatus, 30000); // Check every 30s

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return { isOnline, mode };
}
