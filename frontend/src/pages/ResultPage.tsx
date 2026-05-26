// import { useLocation, useNavigate } from 'react-router-dom';
// import { ArrowLeft, Save, AlertTriangle, AlertCircle, CheckCircle, Pill, ChevronRight, MapPin, ClipboardList } from 'lucide-react';
// import { motion } from 'motion/react';
// import { DiagnosisResult } from '../types/nidaan';
// import { useHistory } from '../hooks/useHistory';
// import { v4 as uuidv4 } from 'uuid';
// import { useState } from 'react';

// export default function ResultPage() {
//   const location = useLocation();
//   const navigate = useNavigate();
//   const state = location.state as { symptoms: string; result: DiagnosisResult; id?: string };
//   const { addRecord } = useHistory();
//   const [saved, setSaved] = useState(!!state?.id);

//   if (!state || !state.result) {
//     return (
//       <div className="flex flex-col items-center justify-center p-8 h-full">
//         <p className="text-text-muted mb-4">No diagnosis data found.</p>
//         <button onClick={() => navigate('/')} className="bg-surface-elevated px-4 py-2 rounded-lg">Go Back</button>
//       </div>
//     );
//   }

//   const { symptoms, result } = state;

//   const handleSave = () => {
//     if (saved) return;
//     const record = {
//       id: uuidv4(),
//       symptoms,
//       result,
//       timestamp: new Date().toISOString()
//     };
//     addRecord(record);
//     setSaved(true);
//   };

//   const isHigh = result.criticality === 'high';
//   const isMedium = result.criticality === 'medium';

//   const containerVariants = {
//     hidden: { opacity: 0 },
//     show: {
//       opacity: 1,
//       transition: { staggerChildren: 0.1 }
//     }
//   };

//   const itemVariants = {
//     hidden: { opacity: 0, y: 10 },
//     show: { opacity: 1, y: 0 }
//   };

//   return (
//     <div className="flex flex-col min-h-full pb-20 relative">
//       {/* Header */}
//       <header className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border flex items-center justify-between p-4 px-4 h-16">
//         <button onClick={() => navigate(-1)} className="p-2 -ml-2 rounded-full hover:bg-surface-elevated transition-colors">
//           <ArrowLeft className="w-6 h-6 text-text-primary" />
//         </button>
//         <h2 className="font-bold text-lg font-display">Result / परिणाम</h2>
//         <button 
//           onClick={handleSave} 
//           disabled={saved}
//           className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${saved ? 'bg-success/20 text-success' : 'bg-surface-elevated text-text-primary hover:bg-border'}`}
//         >
//           {saved ? <CheckCircle className="w-4 h-4" /> : <Save className="w-4 h-4" />}
//           {saved ? 'Saved' : 'Save'}
//         </button>
//       </header>

//       <motion.div 
//         variants={containerVariants}
//         initial="hidden"
//         animate="show"
//         className="p-4 flex flex-col gap-4"
//       >
//         {/* Urgent Banner */}
//         {isHigh && (
//           <motion.div variants={itemVariants} className="bg-danger p-3 rounded-xl flex items-center gap-3">
//             <AlertTriangle className="w-6 h-6 text-white shrink-0" />
//             <p className="text-white font-bold text-sm leading-tight">⚠️ Patient needs immediate referral — show this screen to the family</p>
//           </motion.div>
//         )}

//         {/* Criticality Hero Card */}
//         <motion.div 
//           variants={itemVariants}
//           className={`rounded-2xl p-5 border-l-[6px] shadow-lg relative overflow-hidden ${
//             isHigh 
//               ? 'bg-gradient-to-r from-danger-bg to-[#3a0f0f] border-danger' 
//               : isMedium 
//                 ? 'bg-gradient-to-r from-warning-bg to-[#2d1a0a] border-warning' 
//                 : 'bg-gradient-to-r from-success-bg to-[#0a3d1f] border-success'
//           }`}
//         >
//           {isHigh && <div className="absolute inset-0 border-2 border-danger rounded-2xl animate-pulse" style={{ animationDuration: '2s' }} />}
//           <div className="flex items-center gap-4 mb-4 relative z-10">
//             <div className="text-4xl">
//               {isHigh ? '🔴' : isMedium ? '🟡' : '🟢'}
//             </div>
//             <div>
//               <h3 className="font-bold text-lg uppercase tracking-wider text-white">
//                 Criticality {result.criticality}
//               </h3>
//               <p className="font-hindi text-text-secondary">
//                 {isHigh ? 'अति गंभीर (High)' : isMedium ? 'मध्यम (Medium)' : 'कम गंभीर (Low)'}
//               </p>
//             </div>
//           </div>
//           <div className="mt-4 pt-4 border-t border-white/10 relative z-10">
//             <div className="flex items-center gap-2">
//                <span className="text-xl">{result.refer_to_phc ? '🚑' : '🏠'}</span>
//                <span className="font-medium text-white">
//                  {result.refer_to_phc ? 'Refer to PHC Immediately / PHC भेजें' : 'Home Care Sufficient / घर पर इलाज संभव'}
//                </span>
//             </div>
//           </div>
//         </motion.div>

//         {/* Reason */}
//         <motion.div variants={itemVariants} className="bg-surface rounded-xl p-4 border border-border">
//           <div className="flex items-center gap-2 mb-2">
//             <ClipboardList className="w-5 h-5 text-text-secondary" />
//             <h3 className="font-bold text-white">Reason / कारण</h3>
//           </div>
//           <p className="text-text-primary text-sm leading-relaxed">{result.reason}</p>
//         </motion.div>

//         {/* Red Flags */}
//         {result.red_flags?.length > 0 && (
//           <motion.div 
//             variants={itemVariants} 
//             className={`bg-[#1f0a0a] rounded-xl p-4 border ${isHigh ? 'border-danger animate-pulse' : 'border-danger/30'}`}
//           >
//             <h3 className="font-bold text-danger mb-3 flex items-center gap-2">
//               ⚠️ Red Flags / खतरे के संकेत
//             </h3>
//             <div className="flex flex-col gap-2">
//               {result.red_flags.map((flag, i) => (
//                 <div key={i} className="flex gap-2 items-start py-1">
//                   <AlertCircle className="w-4 h-4 text-danger mt-1 shrink-0" />
//                   <p className="text-red-100 text-sm">{flag}</p>
//                 </div>
//               ))}
//             </div>
//           </motion.div>
//         )}

//         {/* Home Care */}
//         {!isHigh && result.home_care?.length > 0 && (
//           <motion.div variants={itemVariants} className="bg-surface rounded-xl p-4 border border-border">
//             <h3 className="font-bold text-success mb-3 flex items-center gap-2">
//               🏠 Home Care / घरेलू देखभाल
//             </h3>
//             <div className="flex flex-col gap-2">
//               {result.home_care.map((item, i) => (
//                 <div key={i} className="flex gap-2 items-start py-1">
//                   <CheckCircle className="w-4 h-4 text-success mt-1 shrink-0" />
//                   <p className="text-text-primary text-sm">{item}</p>
//                 </div>
//               ))}
//             </div>
//           </motion.div>
//         )}

//         {/* Medicines */}
//         {!isHigh && result.medicines?.length > 0 && (
//           <motion.div variants={itemVariants} className="bg-surface rounded-xl p-4 border border-border">
//              <h3 className="font-bold text-info mb-3 flex items-center gap-2">
//               💊 Medicines / दवाइयां
//             </h3>
//             <div className="flex flex-col gap-3">
//               {result.medicines.map((med, i) => (
//                 <div key={i} className="bg-info-bg rounded-lg p-3 border border-info/30">
//                   <div className="flex items-center gap-2 mb-1">
//                     <Pill className="w-4 h-4 text-info" />
//                     <span className="font-bold text-white text-sm">{med.name}</span>
//                   </div>
//                   <div className="text-xs text-info/80 pl-6 space-y-0.5">
//                     <p>Dosage: {med.dosage}</p>
//                     <p>Duration: {med.duration}</p>
//                   </div>
//                 </div>
//               ))}
//             </div>
//           </motion.div>
//         )}

//         {/* Hindi Advice Box */}
//         {result.advice_in_hindi && (
//           <motion.div variants={itemVariants} className="bg-gradient-to-br from-[#1a2f24] to-[#2c2d1b] rounded-xl p-5 border border-success/20">
//             <h3 className="font-bold text-white mb-3 text-lg flex items-center gap-2">
//               🗣️ सलाह / Advice
//             </h3>
//             <p className="font-hindi text-lg leading-[1.9] text-gray-100">
//               {result.advice_in_hindi}
//             </p>
//           </motion.div>
//         )}
//       </motion.div>

//       {/* FAB for HIGH */}
//       {isHigh && (
//         <div className="fixed bottom-20 left-0 right-0 px-4 max-w-md mx-auto z-20">
//           <button 
//             onClick={() => navigate('/phc')}
//             className="w-full bg-danger text-white h-14 rounded-full font-bold shadow-[0_0_20px_rgba(239,68,68,0.4)] flex items-center justify-center gap-2 text-lg hover:bg-danger/90 active:scale-[0.98] transition-all"
//           >
//             <MapPin className="w-6 h-6" />
//             🚑 PHC Dhundhen / Find PHC <ChevronRight className="w-5 h-5 ml-1" />
//           </button>
//         </div>
//       )}
//     </div>
//   );
// }


"use client";

// app/result/page.tsx
// CHANGES FROM ORIGINAL:
// - Reads real DiagnosisResult from sessionStorage (set by home page)
// - All sections (criticality, red flags, home care, medicines, hindi advice)
//   now render live API data instead of hardcoded placeholders
// - Saves to localStorage history on mount
// - Empty sections are hidden automatically

import { useEffect, useState } from "react";
// import { useRouter } from "../utils/router";
import { useNavigate } from "react-router-dom";
import {
  loadResultFromSession,
  saveToHistory,
} from "../lib/api";
import type { DiagnosisResult, CriticalityLevel } from  "../types/nidaan";

// ─── Criticality config ───────────────────────────────────────────
const CRIT_CONFIG: Record<
  CriticalityLevel,
  { icon: string; label: string; hindiLabel: string; cardClass: string; dotClass: string }
> = {
  low: {
    icon: "🟢",
    label: "LOW",
    hindiLabel: "कम गंभीर",
    cardClass: "bg-gradient-to-r from-[#052e16] to-[#0a3d1f] border-l-4 border-green-500",
    dotClass: "bg-green-500",
  },
  medium: {
    icon: "🟡",
    label: "MEDIUM",
    hindiLabel: "मध्यम",
    cardClass: "bg-gradient-to-r from-[#1c1007] to-[#2d1a0a] border-l-4 border-amber-500",
    dotClass: "bg-amber-500",
  },
  high: {
    icon: "🔴",
    label: "HIGH",
    hindiLabel: "गंभीर",
    cardClass: "bg-gradient-to-r from-[#1f0a0a] to-[#3a0f0f] border-l-4 border-red-500 animate-pulse-border",
    dotClass: "bg-red-500",
  },
};

export default function ResultPage() {
  const navigate = useNavigate();
  const [data, setData] = useState<DiagnosisResult | null>(null);
  const [symptoms, setSymptoms] = useState<string>("");
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const session = loadResultFromSession();
    if (!session) {
      // No result in session — send back to home
      navigate("/");
      return;
    }
    setData(session.result);
    setSymptoms(session.symptoms);

    // Auto-save to history
    saveToHistory(session.symptoms, session.result);
  }, [navigate]);

  if (!data) {
    return (
      <main className="min-h-screen bg-[#0f1117] flex items-center justify-center">
        <div className="text-[#94a3b8] text-sm animate-pulse">
          Loading result...
        </div>
      </main>
    );
  }

  const crit = CRIT_CONFIG[data.criticality];

  return (
    <main className="min-h-screen bg-[#0f1117] text-white pb-28">

      {/* ── Header ── */}
      <div className="sticky top-0 bg-[#0f1117] border-b border-[#2e3347] z-10">
        <div className="max-w-lg mx-auto flex items-center justify-between px-4 py-3">
          <button
            onClick={() => navigate("/")}
            className="text-[#94a3b8] hover:text-white flex items-center gap-1 text-sm"
          >
            ← Back
          </button>
          <span className="font-semibold text-sm">Diagnosis Result / निदान</span>
          <button
            onClick={() => {
              saveToHistory(symptoms, data);
              setSaved(true);
            }}
            className={`text-xs px-3 py-1.5 rounded-full border transition-colors ${
              saved
                ? "border-green-600 text-green-400"
                : "border-[#2e3347] text-[#94a3b8] hover:border-green-600 hover:text-green-400"
            }`}
          >
            {saved ? "✓ Saved" : "Save"}
          </button>
        </div>
      </div>

      <div className="max-w-lg mx-auto px-4 pt-4 space-y-4">

        {/* ── Section 1: Criticality Hero Card ── */}
        <div className={`rounded-2xl p-5 ${crit.cardClass}`}>
          <div className="flex items-start gap-3">
            <span className="text-4xl">{crit.icon}</span>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-white/60 mb-0.5">
                Criticality / गंभीरता
              </p>
              <p className="text-2xl font-bold">
                {crit.label} / {crit.hindiLabel}
              </p>

              {/* PHC Referral banner inside card */}
              <div
                className={`mt-3 flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold ${
                  data.refer_to_phc
                    ? "bg-red-900/60 text-red-300"
                    : "bg-[#0c1a2e]/60 text-blue-300"
                }`}
              >
                <span>{data.refer_to_phc ? "🚑" : "🏠"}</span>
                <div>
                  <div>
                    {data.refer_to_phc
                      ? "Refer to PHC Immediately / PHC भेजें"
                      : "Home Care Sufficient / घर पर इलाज संभव"}
                  </div>
                  <div className="font-normal text-xs opacity-75 mt-0.5 font-noto">
                    {data.refer_to_phc
                      ? "रोगी को तुरंत प्राथमिक स्वास्थ्य केंद्र ले जाएं"
                      : "अभी PHC रेफरल की जरूरत नहीं"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Section 2: Reason ── */}
        <div className="bg-[#1a1d27] border border-[#2e3347] rounded-2xl p-4">
          <p className="text-xs font-bold uppercase tracking-wider text-[#94a3b8] mb-2">
            📋 Assessment Reason / आकलन का कारण
          </p>
          <p className="text-sm leading-relaxed text-[#f1f5f9]">{data.reason}</p>
        </div>

        {/* ── Section 3: Red Flags (hidden if empty) ── */}
        {data.red_flags.length > 0 && (
          <div className="bg-[#1a1d27] border border-red-900 rounded-2xl p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-red-400 mb-3">
              ⚠️ Red Flags / खतरे के संकेत
            </p>
            <div className="space-y-2">
              {data.red_flags.map((flag, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-sm text-red-300
                             border-b border-red-950 pb-2 last:border-0 last:pb-0"
                >
                  <span className="mt-0.5 flex-shrink-0">▲</span>
                  <span>{flag}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Section 4: Home Care (hidden if HIGH or empty) ── */}
        {data.home_care.length > 0 && (
          <div className="bg-[#1a1d27] border border-[#2e3347] rounded-2xl p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-[#94a3b8] mb-3">
              🏠 Home Care / घरेलू देखभाल
            </p>
            <div className="space-y-2">
              {data.home_care.map((item, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-[#f1f5f9]
                                        border-b border-[#2e3347] pb-2 last:border-0 last:pb-0">
                  <span className="text-green-400 mt-0.5 flex-shrink-0">✓</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Section 5: Medicines (hidden if HIGH or empty) ── */}
        {data.medicines.length > 0 && (
          <div className="bg-[#1a1d27] border border-[#2e3347] rounded-2xl p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-[#94a3b8] mb-3">
              💊 Medicines / दवाइयां
            </p>
            <div className="space-y-2">
              {data.medicines.map((med, i) => (
                <div
                  key={i}
                  className="bg-[#22263a] border border-[#2e3347] rounded-xl p-3"
                >
                  <p className="font-semibold text-sm text-white">💊 {med.name}</p>
                  <div className="flex flex-wrap gap-2 mt-1.5">
                    <span className="text-xs bg-[#1a1d27] border border-[#2e3347]
                                     rounded px-2 py-0.5 text-[#94a3b8]">
                      Dose: {med.dosage}
                    </span>
                    <span className="text-xs bg-[#1a1d27] border border-[#2e3347]
                                     rounded px-2 py-0.5 text-[#94a3b8]">
                      Duration: {med.duration}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Section 6: Hindi Advice ── */}
        {data.advice_in_hindi && (
          <div className="bg-gradient-to-br from-[#052e16] to-[#1c1007]
                          border border-green-900 rounded-2xl p-4">
            <p className="text-xs font-bold uppercase tracking-wider text-green-500 mb-3">
              🗣️ Advice in Hindi / हिंदी में सलाह
            </p>
            <p className="text-base leading-[1.9] text-green-100 font-noto">
              {data.advice_in_hindi}
            </p>
          </div>
        )}

        {/* ── FAB: Find PHC (for MEDIUM or HIGH criticality) (Task F4) ── */}
        {(data.criticality === "high" || data.criticality === "medium") && (
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
            className={`fixed bottom-20 left-1/2 -translate-x-1/2 text-white font-bold
                       px-6 py-3 rounded-full shadow-xl flex items-center gap-2 text-sm transition-all
                       hover:scale-105 active:scale-95 duration-200 ${
                         data.criticality === "high"
                           ? "bg-red-600 hover:bg-red-500 shadow-red-950/50 animate-bounce"
                           : "bg-green-600 hover:bg-green-500 shadow-green-950/50"
                       }`}
          >
            🏥 PHC Dhundhen / Find PHC →
          </button>
        )}

      </div>
    </main>
  );
}