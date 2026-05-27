import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, MapPin, Hospital, Clock, Phone, Navigation, AlertCircle } from 'lucide-react';
import { motion } from 'motion/react';
import { usePHCRecommend } from '../hooks/usePHCRecommend';
import type { CriticalityLevel } from '../types/nidaan';

export default function PhcPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Read navigation context params
  const paramDistrict = searchParams.get('district');
  const paramCriticality = searchParams.get('criticality') as CriticalityLevel | null;
  const paramServices = searchParams.get('services');

  const districts = [
    'Paschim Bardhaman',
    'Purba Bardhaman',
    'Hooghly',
    'Howrah',
    'Kolkata',
    'Bankura'
  ];

  const [selectedDistrict, setSelectedDistrict] = useState(paramDistrict || 'Paschim Bardhaman');
  const [coords, setCoords] = useState<{ lat: number; lng: number } | undefined>(undefined);
  // Hook for recommended PHCs

  const { recommend, isLoading, error, results } = usePHCRecommend();

  // 1. Get user coordinates once on mount
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
  (position) => {
    setCoords({
      lat: position.coords.latitude,
      lng: position.coords.longitude
    });
  },
  (err) => {
    console.log('Location error:', err);
    setCoords(null);
  },
  { 
    timeout: 10000,
    enableHighAccuracy: true,  
    maximumAge: 0              
  }
);
    }
  }, []);

  // 2. Fetch recommendations whenever district, coords, or searchParams change
  useEffect(() => {
    if (coords === undefined) return  // still waiting
    const services = paramServices ? paramServices.split(',') : [];

    console.log("Sending to backend:", {  // ← add this
    district: selectedDistrict,
    patient_lat: coords?.lat,
    patient_lng: coords?.lng
  });
    recommend({
      district: selectedDistrict,
      criticality: paramCriticality || 'low',
      required_services: services,
      patient_lat: coords?.lat,
      patient_lng: coords?.lng
    });
  }, [selectedDistrict, coords, paramCriticality, paramServices]);

  const getProgressBarColor = (score: number) => {
    if (score > 0.7) return 'bg-green-500';
    if (score >= 0.4) return 'bg-amber-500';
    return 'bg-red-500';
  };

  // Skeleton Card component
  const SkeletonCard = () => (
    <div className="bg-surface border border-border/50 rounded-xl p-4 animate-pulse">
      <div className="flex gap-3 mb-3">
        <div className="w-10 h-10 rounded-full bg-[#1e293b] shrink-0" />
        <div className="flex-1 space-y-2 py-1">
          <div className="h-4 bg-[#1e293b] rounded w-3/4" />
          <div className="h-3 bg-[#1e293b] rounded w-1/2" />
        </div>
      </div>
      <div className="space-y-2 ml-13 mb-4">
        <div className="h-3 bg-[#1e293b] rounded w-5/6" />
        <div className="h-3 bg-[#1e293b] rounded w-2/3" />
      </div>
      <div className="h-10 bg-[#1e293b] rounded-lg w-full" />
    </div>
  );

  return (
    <div className="flex flex-col min-h-full pb-20">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border flex items-center p-4 px-4 h-16 shadow-sm">
        <button onClick={() => navigate(-1)} className="p-2 -ml-2 rounded-full hover:bg-surface-elevated transition-colors">
          <ArrowLeft className="w-6 h-6 text-text-primary" />
        </button>
        <div className="flex items-center gap-2 ml-2">
          <MapPin className="w-5 h-5 text-info" />
          <h2 className="font-bold text-lg font-display text-white font-noto">Nazdiki PHC / Recommended PHC</h2>
        </div>
      </header>

      <div className="p-4 max-w-lg mx-auto w-full">
        {/* Criticality Banner (Navigated context) */}
        {paramCriticality && (
          <div className={`mb-6 p-4 rounded-xl border flex items-start gap-3 ${
            paramCriticality === 'high'
              ? 'bg-red-950/40 border-red-900/50 text-red-200'
              : 'bg-amber-950/40 border-amber-900/50 text-amber-200'
          }`}>
            <span className="text-xl mt-0.5">{paramCriticality === 'high' ? '🔴' : '🟡'}</span>
            <div className="text-sm font-medium">
              <p className="font-bold">
                {paramCriticality === 'high'
                  ? 'HIGH criticality — showing 24hr PHCs first'
                  : 'MEDIUM criticality — showing nearest PHCs'}
              </p>
              <p className="text-xs opacity-85 mt-1 font-noto">
                {paramCriticality === 'high'
                  ? 'रोगी को तुरंत भर्ती करने के लिए 24 घंटे वाले PHC को प्राथमिकता दी गई है।'
                  : 'सामान्य उपचार और परामर्श के लिए नजदीकी PHC की सूची।'}
              </p>
            </div>
          </div>
        )}

        {/* District Selector */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-text-secondary mb-2">Select District / जिला चुनें</label>
          <div className="relative">
            <select 
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="w-full bg-surface border border-border text-white rounded-xl p-3.5 appearance-none focus:outline-none focus:ring-2 focus:ring-info/50 font-sans"
            >
              {districts.map(d => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-text-muted">
              ▼
            </div>
          </div>
        </div>

        {/* Loading state skeleton */}
        {isLoading ? (
          <div className="flex flex-col gap-4">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : error && results.length === 0 ? (
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }}
            className="text-center py-10 flex flex-col items-center"
          >
            <div className="w-16 h-16 bg-surface-elevated rounded-full flex items-center justify-center mb-4">
              <AlertCircle className="w-8 h-8 text-text-muted" />
            </div>
            <h3 className="text-white font-medium mb-1">Koi PHC nahi mila</h3>
            <p className="text-text-muted text-sm pb-10">Is district mein abhi data nahi hai / No PHCs found</p>
          </motion.div>
        ) : (
          <div className="flex flex-col gap-4">
            {results.map((phc, idx) => (
              <motion.div 
                key={phc.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.1 }}
                className="bg-surface border border-border rounded-xl p-4 overflow-hidden"
              >
                <div className="flex gap-3 mb-3">
                  <div className="mt-1 w-10 h-10 rounded-full bg-info-bg flex items-center justify-center shrink-0">
                    <Hospital className="w-5 h-5 text-info" />
                  </div>
                  <div>
                    <h3 className="font-bold text-white leading-tight mb-1">{phc.name}</h3>
                    <p className="text-xs text-text-secondary flex items-start gap-1">
                      <MapPin className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                      {phc.address}
                    </p>
                  </div>
                </div>

                {/* Score bar */}
                <div className="mb-4 ml-13">
                  <div className="flex justify-between items-center text-[11px] text-text-secondary mb-1">
                    <span className="font-medium text-text-primary">Match Score: {Math.round(phc.service_match_score * 100)}%</span>
                    <span className="text-text-muted italic">{phc.match_reason}</span>
                  </div>
                  <div className="w-full bg-[#1e293b] h-1.5 rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${getProgressBarColor(phc.service_match_score)} transition-all duration-500`}
                      style={{ width: `${phc.service_match_score * 100}%` }}
                    />
                  </div>
                </div>

                <div className="space-y-1.5 mb-4 ml-13">
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <Clock className="w-3.5 h-3.5" />
                    <span>{phc.timing}</span>
                    {phc.open_24hr && <span className="text-success font-semibold ml-1 bg-success/10 px-1.5 py-0.5 rounded text-[10px]">24x7 OPEN</span>}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-text-muted">
                    <Phone className="w-3.5 h-3.5" />
                    <span>{phc.contact || 'Contact not available'}</span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-1.5 mb-4 ml-13">
                  {phc.services.map(s => (
                    <span key={s} className="px-2 py-0.5 bg-surface-elevated rounded text-[10px] uppercase tracking-wider font-medium text-text-secondary">
                      {s}
                    </span>
                  ))}
                  {phc.ambulance && (
                    <span className="px-2 py-0.5 bg-red-950 text-red-400 border border-red-900 rounded text-[10px] uppercase tracking-wider font-bold">
                      Ambulance 🚑
                    </span>
                  )}
                </div>

                <div className="flex gap-2 ml-13">
                  {phc.latitude && phc.longitude ? (
                    <button 
                      onClick={() => {
                        const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${phc.latitude},${phc.longitude}`;
                        window.open(mapsUrl, '_blank');
                      }}
                      className="flex-1 h-10 bg-[#eef2ff] hover:bg-[#e0e7ff] text-info font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-colors text-sm"
                    >
                      <Navigation className="w-4 h-4" />
                      Directions
                    </button>
                  ) : (
                    <button 
                      disabled
                      className="flex-1 h-10 bg-[#1e293b]/50 text-text-muted cursor-not-allowed font-medium rounded-lg flex items-center justify-center gap-1.5 text-sm"
                      title="Location details unavailable"
                    >
                      <Navigation className="w-4 h-4" />
                      Location N/A
                    </button>
                  )}

                  {phc.contact ? (
                    <a 
                      href={`tel:${phc.contact}`}
                      className="px-4 h-10 border border-border hover:bg-surface-elevated text-white rounded-lg flex items-center justify-center gap-1.5 transition-colors text-sm"
                    >
                      <Phone className="w-4 h-4" />
                      Call
                    </a>
                  ) : (
                    <button 
                      disabled
                      className="px-4 h-10 border border-border/40 text-text-muted cursor-not-allowed rounded-lg flex items-center justify-center gap-1.5 text-sm"
                      title="Contact details unavailable"
                    >
                      <Phone className="w-4 h-4" />
                      Call N/A
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
