import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { 
  ArrowLeft, MapPin, Hospital, Clock, Phone, Navigation, 
  AlertCircle, ShieldAlert, Sparkles, PhoneCall, Compass, CheckCircle2 
} from "lucide-react";
import { motion } from "motion/react";
import { usePHCRecommend } from "../hooks/usePHCRecommend";
import type { CriticalityLevel } from "../types/nidaan";

export default function PhcPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Read navigation context params
  const paramDistrict = searchParams.get("district");
  const paramCriticality = searchParams.get("criticality") as CriticalityLevel | null;
  const paramServices = searchParams.get("services");

  const districts = [
    "Paschim Bardhaman",
    "Purba Bardhaman",
    "Hooghly",
    "Howrah",
    "Kolkata",
    "Bankura"
  ];

  const [selectedDistrict, setSelectedDistrict] = useState(paramDistrict || "Paschim Bardhaman");
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
          console.warn("Location error:", err);
          setCoords(null as any);
        },
        { 
          timeout: 10000,
          enableHighAccuracy: true,  
          maximumAge: 0              
        }
      );
    } else {
      setCoords(null as any);
    }
  }, []);

  // 2. Fetch recommendations whenever district, coords, or searchParams change
  useEffect(() => {
    if (coords === undefined) return; // wait for geolocation resolves
    const services = paramServices ? paramServices.split(",") : [];

    recommend({
      district: selectedDistrict,
      criticality: paramCriticality || "low",
      required_services: services,
      patient_lat: coords?.lat,
      patient_lng: coords?.lng
    });
  }, [selectedDistrict, coords, paramCriticality, paramServices]);

  const getProgressBarColor = (score: number) => {
    if (score > 0.7) return "bg-success";
    if (score >= 0.4) return "bg-warning";
    return "bg-danger";
  };

  const getProgressBarBg = (score: number) => {
    if (score > 0.7) return "bg-success/10 text-success";
    if (score >= 0.4) return "bg-warning/10 text-warning";
    return "bg-danger/10 text-danger";
  };

  // Skeleton Card component
  const SkeletonCard = () => (
    <div className="bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700/60 rounded-3xl p-5 animate-pulse space-y-4">
      <div className="flex gap-3">
        <div className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-700 shrink-0" />
        <div className="flex-1 space-y-2 py-1">
          <div className="h-4 bg-slate-100 dark:bg-slate-700 rounded-full w-3/4" />
          <div className="h-3 bg-slate-100 dark:bg-slate-700 rounded-full w-1/2" />
        </div>
      </div>
      <div className="space-y-2 pt-2">
        <div className="h-3 bg-slate-100 dark:bg-slate-700 rounded-full w-full" />
        <div className="h-3 bg-slate-100 dark:bg-slate-700 rounded-full w-5/6" />
      </div>
      <div className="flex gap-2 pt-2">
        <div className="h-10 bg-slate-100 dark:bg-slate-700 rounded-xl flex-1" />
        <div className="h-10 bg-slate-100 dark:bg-slate-700 rounded-xl w-20" />
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      
      {/* ── Page Header ── */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-xl text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h2 className="font-display font-extrabold text-2xl text-slate-900 dark:text-slate-100 tracking-tight flex items-center gap-1.5">
            <Hospital className="w-6 h-6 text-info shrink-0" />
            <span>PHC Recommendation</span>
          </h2>
          <p className="text-text-secondary text-xs font-noto mt-0.5">प्राथमिक स्वास्थ्य केंद्र (रेफरल मार्गदर्शन)</p>
        </div>
      </div>

      {/* ── Navigated patient context banner ── */}
      {paramCriticality && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className={`p-4.5 rounded-2xl border flex items-start gap-3.5 shadow-sm ${
            paramCriticality === "high"
              ? "bg-danger-bg border-danger/20 text-danger"
              : "bg-warning-bg border-warning/20 text-warning-800"
          }`}
        >
          <div className="shrink-0 mt-0.5">
            {paramCriticality === "high" ? (
              <ShieldAlert className="w-5 h-5 text-danger animate-pulse" />
            ) : (
              <AlertCircle className="w-5 h-5 text-warning" />
            )}
          </div>
          <div className="text-xs leading-relaxed font-semibold">
            <p className="font-bold text-sm">
              {paramCriticality === "high"
                ? "HIGH URGENCY: Showing 24/7 PHCs First"
                : "MEDIUM URGENCY: Showing Nearest Care Facilities"}
            </p>
            <p className="opacity-90 font-noto mt-1 text-[11px] leading-relaxed">
              {paramCriticality === "high"
                ? "रोगी की स्थिति अति गंभीर है। तुरंत आपातकालीन उपचार और एम्बुलेंस सुविधा वाले स्वास्थ्य केंद्र से संपर्क करें।"
                : "मरीज की सामान्य निगरानी और विशेषज्ञ उपचार हेतु नजदीकी केंद्रों की सूची।"}
            </p>
          </div>
        </motion.div>
      )}

      {/* ── District Dropdown Selector ── */}
      <div className="bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 rounded-2xl p-4 md:p-5 shadow-xs">
        <label className="block text-xs font-extrabold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-2">
          Select District / ज़िला चुनें
        </label>
        <div className="relative">
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-slate-800 dark:text-slate-100 font-bold rounded-xl p-3.5 appearance-none focus:outline-none focus:bg-white dark:focus:bg-slate-600 focus:border-info focus:ring-4 focus:ring-info/5 transition-all text-sm cursor-pointer"
          >
            {districts.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 text-xs">
            ▼
          </div>
        </div>
      </div>

      {/* ── PHC Recommendation Results List ── */}
      {isLoading ? (
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : error && results.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-16 bg-white dark:bg-slate-800 border border-slate-200/60 dark:border-slate-700/60 rounded-3xl p-6 shadow-xs flex flex-col items-center"
        >
          <div className="w-16 h-16 bg-slate-50 dark:bg-slate-700 border border-slate-100 dark:border-slate-600 rounded-full flex items-center justify-center mb-4 text-slate-300 dark:text-slate-500">
            <AlertCircle className="w-7 h-7" />
          </div>
          <h3 className="text-slate-800 dark:text-slate-200 font-extrabold text-base mb-1">कोई स्वास्थ्य केंद्र नहीं मिला</h3>
          <p className="text-text-muted text-sm font-noto max-w-xs mx-auto">
            {error || "इस जिले में वर्तमान में कोई डेटा उपलब्ध नहीं है / No PHCs found in this district"}
          </p>
        </motion.div>
      ) : (
        <div className="space-y-5">
          {results.map((phc, idx) => (
            <motion.div
              key={phc.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              className="bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 hover:border-info/40 rounded-3xl p-5 md:p-6 shadow-xs hover:shadow-md transition-all duration-200"
            >
              {/* Header Info */}
              <div className="flex gap-4 mb-4">
                <div className="w-12 h-12 rounded-2xl  flex items-center justify-center text-info shrink-0 select-none">
                  <img src="/src/assets/hos_g.png" alt="phc-icon" className="w-12 h-12" />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="font-display font-extrabold text-slate-900 dark:text-slate-100 leading-tight mb-1 text-base md:text-lg">
                    {phc.name}
                  </h3>
                  <p className="text-xs text-text-secondary flex items-start gap-1 font-noto">
                    <MapPin className="w-3.5 h-3.5 mt-0.5 shrink-0 text-slate-400" />
                    <span className="leading-relaxed">{phc.address}</span>
                  </p>
                </div>
              </div>

              {/* Match Score & Metrics */}
              <div className="bg-slate-50/50 dark:bg-slate-700/40 border border-slate-100 dark:border-slate-600/60 rounded-2xl p-3.5 mb-4">
                <div className="flex justify-between items-center text-xs mb-2">
                  <span className="font-extrabold text-slate-700 dark:text-slate-300 flex items-center gap-1">
                    <Sparkles className="w-3.5 h-3.5 text-info" />
                    <span>Match Compatibility:</span>
                    <span className={`px-2 py-0.5 rounded font-mono font-bold ${getProgressBarBg(phc.service_match_score)}`}>
                      {Math.round(phc.service_match_score * 100)}%
                    </span>
                  </span>
                </div>
                <div className="w-full bg-slate-200/60 dark:bg-slate-600/60 h-1.5 rounded-full overflow-hidden mb-2">
                  <div
                    className={`h-full ${getProgressBarColor(phc.service_match_score)} transition-all duration-700`}
                    style={{ width: `${phc.service_match_score * 100}%` }}
                  />
                </div>
                <p className="text-[10px] text-text-muted italic leading-relaxed font-noto">
                  Match reasoning: {phc.match_reason}
                </p>
              </div>

              {/* Facility details */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-text-secondary mb-4">
                <div className="flex items-center gap-2 font-medium bg-slate-50 dark:bg-slate-700/50 px-3 py-2 rounded-xl">
                  <Clock className="w-4 h-4 text-slate-400 shrink-0" />
                  <span className="truncate">{phc.timing}</span>
                  {phc.open_24hr && (
                    <span className="ml-auto flex items-center gap-1 text-[9px] font-black uppercase tracking-wider bg-success-bg border border-success/20 text-success px-1.5 py-0.5 rounded">
                      <span className="w-1.5 h-1.5 rounded-full bg-success animate-ping" />
                      <span>24x7</span>
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 font-medium bg-slate-50 dark:bg-slate-700/50 px-3 py-2 rounded-xl">
                  <Phone className="w-4 h-4 text-slate-400 shrink-0" />
                  <span className="truncate font-mono">{phc.contact || "No Phone Contact"}</span>
                </div>
              </div>

              {/* Services List */}
              <div className="flex flex-wrap gap-1.5 mb-5">
                {phc.services.map((s) => (
                  <span
                    key={s}
                    className="px-2.5 py-1 bg-slate-100 dark:bg-slate-700 border border-slate-200/50 dark:border-slate-600/50 rounded-lg text-[10px] uppercase tracking-wider font-bold text-slate-600 dark:text-slate-300 flex items-center gap-1"
                  >
                    <CheckCircle2 className="w-3 h-3 text-info" />
                    <span>{s}</span>
                  </span>
                ))}
                {phc.ambulance && (
                  <span className="px-2.5 py-1 bg-red-50 dark:bg-red-900/20 border border-red-200/60 dark:border-red-800/30 rounded-lg text-[10px] uppercase tracking-wider font-black text-rose-600 animate-pulse flex items-center gap-1 shadow-xs shadow-red-100/50">
                    🚑 Emergency Ambulance
                  </span>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-2.5 pt-2 border-t border-slate-100 dark:border-slate-700">
                {phc.latitude && phc.longitude ? (
                  <button
                    onClick={() => {
                      const mapsUrl = `https://www.google.com/maps/dir/?api=1&destination=${phc.latitude},${phc.longitude}`;
                      window.open(mapsUrl, "_blank");
                    }}
                    className="flex-1 h-11 bg-info hover:bg-info/95 text-white font-bold rounded-xl flex items-center justify-center gap-1.5 transition-all text-xs shadow-md shadow-info/10 cursor-pointer"
                  >
                    <Compass className="w-4 h-4 shrink-0" />
                    <span>GET DIRECTIONS</span>
                  </button>
                ) : (
                  <button
                    disabled
                    className="flex-1 h-11 bg-slate-100 dark:bg-slate-700 text-slate-400 cursor-not-allowed font-bold rounded-xl flex items-center justify-center gap-1.5 text-xs border border-slate-200/50 dark:border-slate-600/50"
                  >
                    <Compass className="w-4 h-4 shrink-0" />
                    <span>DIRECTIONS N/A</span>
                  </button>
                )}

                {phc.contact ? (
                  <a
                    href={`tel:${phc.contact}`}
                    className="px-5 h-11 border border-slate-200 dark:border-slate-700 hover:border-info/40 hover:bg-slate-50 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold rounded-xl flex items-center justify-center gap-1.5 transition-all text-xs cursor-pointer"
                  >
                    <PhoneCall className="w-4 h-4 shrink-0 text-info" />
                    <span>CALL</span>
                  </a>
                ) : (
                  <button
                    disabled
                    className="px-5 h-11 border border-slate-200 dark:border-slate-700 text-slate-300 dark:text-slate-600 cursor-not-allowed font-bold rounded-xl flex items-center justify-center gap-1.5 text-xs"
                  >
                    <PhoneCall className="w-4 h-4 shrink-0 text-slate-200 dark:text-slate-600" />
                    <span>CALL N/A</span>
                  </button>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

    </div>
  );
}
