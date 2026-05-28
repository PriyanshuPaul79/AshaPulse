import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { 
  ArrowLeft, Check, CheckCircle2, AlertTriangle, AlertCircle, 
  MapPin, Pill, ClipboardList, Bookmark, BookmarkCheck, HeartPulse, ChevronRight
} from "lucide-react";
import { loadResultFromSession, saveToHistory } from "../lib/api";
import type { DiagnosisResult, CriticalityLevel } from "../types/nidaan";

// ─── Severity Level Configuration ──────────────────────────────
interface SeverityStyle {
  label: string;
  hindiLabel: string;
  bgClass: string;
  badgeClass: string;
  glowClass: string;
  icon: string;
}

const SEVERITY_CONFIG: Record<CriticalityLevel, SeverityStyle> = {
  low: {
    label: "LOW SEVERITY",
    hindiLabel: "कम गंभीर (सामान्य)",
    bgClass: "bg-success-bg/60 border-success/20 text-success",
    badgeClass: "bg-success text-white shadow-sm shadow-success/20",
    glowClass: "shadow-emerald-100/50 border-success",
    icon: "🟢"
  },
  medium: {
    label: "MEDIUM SEVERITY",
    hindiLabel: "मध्यम गंभीर (निगरानी रखें)",
    bgClass: "bg-warning-bg/60 border-warning/20 text-warning",
    badgeClass: "bg-warning text-slate-900 shadow-sm shadow-warning/20 font-bold",
    glowClass: "shadow-amber-100/50 border-warning",
    icon: "🟡"
  },
  high: {
    label: "HIGH SEVERITY",
    hindiLabel: "अति गंभीर (आपातकालीन स्थिति)",
    bgClass: "bg-danger-bg/60 border-danger/20 text-danger",
    badgeClass: "bg-danger text-white shadow-sm shadow-danger/20 animate-pulse",
    glowClass: "shadow-red-100/80 animate-pulse-border-red border-danger",
    icon: "🔴"
  }
};

export default function ResultPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DiagnosisResult | null>(null);
  const [symptoms, setSymptoms] = useState<string>("");
  const [saved, setSaved] = useState(false);
  
  // Interactive checklist state for Home Care
  const [checkedGuidelines, setCheckedGuidelines] = useState<Record<number, boolean>>({});

  useEffect(() => {
    const session = loadResultFromSession();
    if (!session) {
      // No result in session — go back home
      navigate("/");
      return;
    }
    setData(session.result);
    setSymptoms(session.symptoms);

    // Auto-save to local history on diagnostic completion
    saveToHistory(session.symptoms, session.result);
  }, [navigate]);

  if (!data) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <HeartPulse className="w-10 h-10 text-info animate-pulse" />
          <span className="text-text-muted text-sm">Loading result...</span>
        </div>
      </div>
    );
  }

  const sev = SEVERITY_CONFIG[data.criticality];
  const isHigh = data.criticality === "high";
  const isMedium = data.criticality === "medium";

  // Toggle helper for the checklist
  const toggleGuideline = (idx: number) => {
    setCheckedGuidelines(prev => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  return (
    <div className="pb-32">
      
      {/* ── Top Header ── */}
      <div className="sticky top-0 bg-white/80 backdrop-blur-md border-b border-border z-10 -mx-4 px-4 py-3 mb-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-50 transition-all cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back</span>
          </button>
          
          <h2 className="font-display font-extrabold text-sm text-slate-800">
            Diagnosis Result / निदान विवरण
          </h2>
          
          <button
            onClick={() => {
              saveToHistory(symptoms, data);
              setSaved(true);
            }}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-full border text-xs font-bold transition-all cursor-pointer ${
              saved
                ? "bg-success-bg border-success/30 text-success"
                : "border-slate-200 text-slate-600 hover:border-success/40 hover:text-success"
            }`}
          >
            {saved ? (
              <>
                <BookmarkCheck className="w-3.5 h-3.5" />
                <span>Saved</span>
              </>
            ) : (
              <>
                <Bookmark className="w-3.5 h-3.5" />
                <span>Save</span>
              </>
            )}
          </button>
        </div>
      </div>

      <div className="space-y-6">

        {/* ── EMERGENCY REFERRAL HERO BANNER (if HIGH criticality) ── */}
        {isHigh && (
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="bg-danger text-white p-5 rounded-2xl flex items-start gap-4 shadow-lg shadow-danger/20 border border-red-600 animate-pulse-glow"
          >
            <div className="p-3 bg-white/10 rounded-2xl shrink-0">
              <AlertTriangle className="w-7 h-7 text-white animate-bounce" />
            </div>
            <div className="space-y-1">
              <h4 className="font-display font-black text-lg tracking-tight uppercase">
                EMERGENCY REFERRAL REQUIRED
              </h4>
              <p className="font-noto text-sm font-bold text-red-50 leading-relaxed">
                रोगी को तुरंत नजदीकी प्राथमिक स्वास्थ्य केंद्र (PHC) ले जाएं। यह एक अति गंभीर आपातकालीन स्थिति है।
              </p>
            </div>
          </motion.div>
        )}

        {/* ── SECTION 1: SEVERITY HERO CARD ── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={`bg-white border rounded-3xl p-5 md:p-6 shadow-md ${sev.glowClass}`}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-4xl shrink-0 select-none">{sev.icon}</span>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wider text-text-muted mb-0.5">
                  Severity Rating / मरीज की गंभीरता
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`text-xs font-black px-2.5 py-1 rounded-md tracking-wider ${sev.badgeClass}`}>
                    {sev.label}
                  </span>
                  <span className="text-slate-800 font-bold text-base md:text-lg font-noto">
                    {sev.hindiLabel}
                  </span>
                </div>
              </div>
            </div>

            {/* Referral / Home Care status pill */}
            <div className={`p-3 rounded-2xl border text-xs font-bold flex items-center gap-2 ${
              data.refer_to_phc
                ? "bg-danger-bg border-danger/10 text-danger"
                : "bg-success-bg border-success/10 text-success"
            }`}>
              <span className="text-lg shrink-0">{data.refer_to_phc ? "🚑" : "🏠"}</span>
              <div className="leading-tight">
                <div>{data.refer_to_phc ? "PHC Refer Needed / रेफर करें" : "Home Care Sufficient / घरेलू उपचार"}</div>
                <div className="text-[10px] font-medium opacity-85 font-noto mt-0.5">
                  {data.refer_to_phc ? "प्राथमिक स्वास्थ्य केंद्र भेजें" : "घर पर उपचार संभव"}
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* ── SECTION 2: CLINICAL REASONING CARD ── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="bg-white border border-slate-200/80 rounded-3xl p-5 md:p-6 shadow-xs"
        >
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-3 flex items-center gap-1.5">
            <ClipboardList className="w-4 h-4 text-info" />
            <span>Clinical Reasoning / निदान का मुख्य कारण</span>
          </h4>
          <p className="text-sm md:text-base leading-relaxed text-slate-700 font-medium">
            {data.reason}
          </p>
        </motion.div>

        {/* ── SECTION 3: HINDI ADVICE BOX ── */}
        {data.advice_in_hindi && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gradient-to-br from-info-bg to-emerald-50/20 border border-info/10 rounded-3xl p-6 shadow-sm"
          >
            <h4 className="text-xs font-bold uppercase tracking-wider text-info mb-3 flex items-center gap-1.5">
              🗣️ Hindi Advice / हिंदी में महत्वपूर्ण सलाह
            </h4>
            <p className="font-hindi text-lg md:text-xl font-bold leading-relaxed text-slate-800 select-all">
              {data.advice_in_hindi}
            </p>
          </motion.div>
        )}

        {/* ── SECTION 4: RED FLAGS CARD (hidden if empty) ── */}
        {data.red_flags.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="bg-red-50/50 border border-danger/30 rounded-3xl p-5 md:p-6 shadow-xs"
          >
            <h4 className="text-xs font-bold uppercase tracking-wider text-danger mb-4 flex items-center gap-1.5">
              <AlertCircle className="w-4.5 h-4.5 text-danger animate-pulse" />
              <span>Danger Signs / खतरे के लक्षण (Red Flags)</span>
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {data.red_flags.map((flag, i) => (
                <div
                  key={i}
                  className="bg-white border border-danger/10 rounded-xl p-3.5 text-sm text-red-950 font-semibold font-noto flex gap-2.5 items-start"
                >
                  <span className="w-2 h-2 rounded-full bg-danger shrink-0 mt-1.5" />
                  <span>{flag}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* ── SECTION 5: HOME CARE PROTOCOLS (hidden if empty) ── */}
        {data.home_care.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-white border border-slate-200/80 rounded-3xl p-5 md:p-6 shadow-xs"
          >
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-1 flex items-center gap-1.5">
              <CheckCircle2 className="w-4.5 h-4.5 text-success" />
              <span>Home Care protocols / घरेलू उपचार एवं देखभाल</span>
            </h4>
            <p className="text-[10px] text-text-muted mb-4">ASHA workers can check off steps as they instruct the family.</p>
            
            <div className="space-y-2">
              {data.home_care.map((item, i) => {
                const isChecked = !!checkedGuidelines[i];
                return (
                  <button
                    key={i}
                    onClick={() => toggleGuideline(i)}
                    className={`w-full text-left p-3.5 rounded-xl border text-sm transition-all duration-150 flex items-start gap-3 cursor-pointer ${
                      isChecked 
                        ? "bg-success-bg/30 border-success/20 text-slate-500 line-through" 
                        : "bg-slate-50/50 border-slate-200/80 text-slate-700 hover:bg-slate-50 font-semibold"
                    }`}
                  >
                    <div className={`w-5 h-5 rounded-md border shrink-0 mt-0.5 flex items-center justify-center transition-all ${
                      isChecked 
                        ? "bg-success border-success text-white" 
                        : "bg-white border-slate-300"
                    }`}>
                      {isChecked && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                    </div>
                    <span className="font-noto">{item}</span>
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}

        {/* ── SECTION 6: MEDICINES TABLE/CARDS (hidden if empty) ── */}
        {data.medicines.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.25 }}
            className="bg-white border border-slate-200/80 rounded-3xl p-5 md:p-6 shadow-xs"
          >
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-4 flex items-center gap-1.5">
              <Pill className="w-4.5 h-4.5 text-info animate-[spin_4s_linear_infinite]" />
              <span>Medicines / सुझाई गई दवाइयां</span>
            </h4>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              {data.medicines.map((med, i) => (
                <div
                  key={i}
                  className="bg-info-bg/40 border border-info/10 rounded-2xl p-4 flex gap-3.5 items-start"
                >
                  <div className="p-2.5 bg-white border border-info/20 rounded-xl text-info shrink-0 select-none shadow-xs">
                    💊
                  </div>
                  <div className="space-y-1 min-w-0">
                    <p className="font-bold text-slate-800 text-sm md:text-base truncate">
                      {med.name}
                    </p>
                    <div className="space-y-0.5 text-xs text-text-secondary">
                      <p className="flex items-center gap-1">
                        <span className="font-bold text-slate-600">Dose:</span> 
                        <span className="truncate">{med.dosage}</span>
                      </p>
                      <p className="flex items-center gap-1">
                        <span className="font-bold text-slate-600">Duration:</span> 
                        <span className="truncate">{med.duration}</span>
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

      </div>

      {/* ── BOTTOM REFERRAL PHC ACTION BLOCK (Task F4 / Medium & High) ── */}
      {(isHigh || isMedium) && (
        <div className="fixed bottom-22 left-1/2 -translate-x-1/2 w-[90%] max-w-sm z-30 animate-bounce">
          <button
            onClick={() => {
              const services = data.suggested_services ? data.suggested_services.join(",") : "";
              const query = new URLSearchParams({
                district: "Paschim Bardhaman",
                criticality: data.criticality,
                services: services
              }).toString();
              navigate(`/phc?${query}`);
            }}
            className={`w-full text-white font-bold h-14 rounded-2xl shadow-xl flex items-center justify-center gap-2 text-sm hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 cursor-pointer ${
              isHigh
                ? "bg-danger shadow-danger/25 hover:bg-red-500"
                : "bg-warning text-slate-900 shadow-warning/25 hover:bg-amber-400"
            }`}
          >
            <MapPin className="w-5 h-5 shrink-0" />
            <span className="font-noto">PHC ढूंढें / Locate Nearby PHC</span>
            <ChevronRight className="w-4.5 h-4.5 shrink-0 ml-0.5" />
          </button>
        </div>
      )}

    </div>
  );
}