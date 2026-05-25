// import { useState, useEffect } from 'react';
// import { useNavigate } from 'react-router-dom';
// import { Activity, Stethoscope } from 'lucide-react';
// import { motion } from 'motion/react';
// import { useDiagnose } from '../hooks/useDiagnose';
// import { useBackendStatus } from '../hooks/useBackendStatus';

// const QUICK_CHIPS = [
//   "बुखार + दस्त",
//   "शिशु बुखार",
//   "सांस की तकलीफ",
//   "सांप का काटना"
// ];

// const QUICK_CHIPS_MAPPING: Record<string, string> = {
//   "बुखार + दस्त": "Bacche ko 2 din se bukhaar hai 38.5°C, dast bhi ho raha hai aur ulti bhi",
//   "शिशु बुखार": "6 mahine ke bacche ko tej bukhaar hai, doodh nahi pee raha",
//   "सांस की तकलीफ": "3 din se khaasi hai aur saans lene mein takleef ho rahi hai, pasli chal rahi hai",
//   "सांप का काटना": "Khet mein kaam karte waqt saanp ne kaat liya, pair mein sujan aur dard hai"
// };

// export default function HomePage() {
//   const [symptoms, setSymptoms] = useState('');
//   const navigate = useNavigate();
//   const { diagnose, isLoading, error, result } = useDiagnose();
//   const { isOnline, mode } = useBackendStatus();

//   useEffect(() => {
//     if (result) {
//       navigate('/result', { state: { symptoms, result } });
//     }
//   }, [result, navigate, symptoms]);

//   const handleDiagnose = async () => {
//     if (!symptoms.trim()) {
//       return;
//     }
    
//     await diagnose(symptoms);
//   };

//   return (
//     <motion.div 
//       initial={{ opacity: 0, y: 10 }}
//       animate={{ opacity: 1, y: 0 }}
//       className="p-4 flex flex-col h-full"
//     >
//       {/* Header */}
//       <div className="flex justify-between items-start mb-8 pt-4">
//         <div>
//           <h1 className="font-display text-3xl font-bold flex items-center gap-2 text-white">
//             <span className="text-xl">🏥</span> NiDaan
//           </h1>
//           <p className="font-hindi text-text-secondary mt-1">निदान - एआई स्वास्थ्य सहायक</p>
//         </div>
        
//         {/* Backend Status */}
//         <div className="flex items-center gap-1.5 bg-surface-elevated px-2.5 py-1 rounded-full text-xs font-medium border border-border">
//           <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-success' : 'bg-danger'}`} />
//           <span className={isOnline ? 'text-success' : 'text-danger'}>
//             {isOnline ? (mode ? `Gruq` : 'Online') : 'Offline'}
//           </span>
//         </div>
//       </div>

//       {/* Input Card */}
//       <div className="bg-surface border border-border rounded-2xl p-5 shadow-lg flex-1 flex flex-col">
//         <h2 className="text-lg font-bold text-white mb-1">Lakshan Batayein / Describe Symptoms</h2>
//         <p className="font-hindi text-sm text-text-secondary mb-4">हिंदी, Hinglish, या English में लिखें</p>
        
//         {/* Quick Chips */}
//         <div className="flex flex-wrap gap-2 mb-4">
//           {QUICK_CHIPS.map(chip => (
//             <motion.button
//               key={chip}
//               whileTap={{ scale: 0.95 }}
//               onClick={() => setSymptoms(QUICK_CHIPS_MAPPING[chip])}
//               className="px-3 py-1.5 bg-surface-elevated border border-border rounded-lg text-sm font-hindi text-text-primary hover:bg-border transition-colors"
//             >
//               {chip}
//             </motion.button>
//           ))}
//         </div>

//         {/* Textarea */}
//         <div className="relative flex-1 min-h-[200px]">
//           <textarea
//             value={symptoms}
//             onChange={(e) => setSymptoms(e.target.value)}
//             placeholder="उदाहरण: Bacche ko 2 din se bukhaar hai 38.5°C, dast bhi ho raha hai..."
//             className="w-full h-full bg-surface-elevated border border-border rounded-xl p-4 text-white placeholder-text-muted font-sans resize-none focus:outline-none focus:ring-2 focus:ring-success/50"
//           />
//           <div className="absolute bottom-4 right-4 text-xs text-text-muted font-mono">
//             {symptoms.length}
//           </div>
//         </div>

//         {/* Submit Button */}
//         {error && (
//           <div className="mt-4 p-3 bg-danger/10 border border-danger/20 rounded-xl">
//             <p className="text-danger text-sm">{error}</p>
//           </div>
//         )}
//         <button
//           onClick={handleDiagnose}
//           disabled={!symptoms.trim() || isLoading}
//           className="mt-4 w-full h-14 bg-success hover:bg-success/90 active:bg-success/80 text-success-bg font-bold rounded-xl flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-lg"
//         >
//           {isLoading ? (
//             <>
//               <Activity className="w-6 h-6 animate-spin" />
//               Vishleshan ho raha hai...
//             </>
//           ) : (
//             <>
//               <Stethoscope className="w-6 h-6" />
//               Jaanch Karein / Diagnose
//             </>
//           )}
//         </button>
//       </div>
//     </motion.div>
//   );
// }




"use client";

// app/page.tsx
// CHANGES FROM ORIGINAL:
// 1. handleDiagnose now calls POST /diagnose via lib/api.ts
// 2. Result saved to sessionStorage before navigating
// 3. Loading state shows spinner during API call
// 4. Error states for connection error, timeout, server error
// 5. useBackendStatus hook added for live TopNav badge
// Keep all your existing UI/design exactly as-is — only the handleDiagnose
// function and state variables below need to change.

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { diagnose, saveResultToSession, checkHealth } from "../lib/api";

// ─── Paste these state variables into your existing component ────
//
// const [symptoms, setSymptoms]   = useState("");        ← already exists
// const [isLoading, setIsLoading] = useState(false);     ← ADD THIS
// const [error, setError]         = useState<string | null>(null);  ← ADD THIS
// const [backendMode, setBackendMode] = useState<string | null>(null); ← ADD THIS

// ─── Replace your handleDiagnose with this ───────────────────────

export default function HomePage() {
  const navigate = useNavigate();
  const [symptoms, setSymptoms] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendMode, setBackendMode] = useState<string | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState(false);

  // Check backend status on mount and every 30 seconds
  useEffect(() => {
    const check = async () => {
      try {
        const health = await checkHealth();
        setIsBackendOnline(true);
        setBackendMode(health.mode);
      } catch {
        setIsBackendOnline(false);
        setBackendMode(null);
      }
    };

    check();
    const interval = setInterval(check, 30_000);
    return () => clearInterval(interval);
  }, []);

  const handleDiagnose = async () => {
    // Validate input
    if (!symptoms.trim()) {
      setError("Please enter symptoms / कृपया लक्षण दर्ज करें");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // 1. Call FastAPI /diagnose
      const result = await diagnose(symptoms.trim());

      // 2. Save result + symptoms to sessionStorage so /result can read it
      saveResultToSession(symptoms.trim(), result);

      // 3. Navigate to result page
      navigate("/result");

    } catch (err: unknown) {
      if (err instanceof Error) {
        // Connection refused — backend not running
        if (
          err.message.includes("fetch") ||
          err.message.includes("Failed to fetch") ||
          err.message.includes("NetworkError")
        ) {
          setError(
            "Cannot reach backend. Make sure FastAPI is running on port 8000.\n" +
            "सर्वर से जुड़ नहीं पाया। कृपया बैकएंड जांचें।"
          );
        }
        // Timeout — Ollama taking too long
        else if (
          err.name === "TimeoutError" ||
          err.message.includes("timeout")
        ) {
          setError(
            "Analysis is taking too long. Try again.\n" +
            "विश्लेषण में बहुत समय लग रहा है। पुनः प्रयास करें।"
          );
        }
        // Server returned an error
        else {
          setError(`Error: ${err.message}`);
        }
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────────
  // KEEP YOUR EXISTING JSX EXACTLY AS-IS.
  // Just wire up the values below to your existing elements:
  //
  // textarea:       value={symptoms} onChange={(e) => setSymptoms(e.target.value)}
  // submit button:  onClick={handleDiagnose} disabled={isLoading}
  // loading state:  {isLoading && <Spinner />}
  // error display:  {error && <ErrorBox message={error} />}
  // backend badge:  isBackendOnline, backendMode
  // ─────────────────────────────────────────────────────────────────

  return (
    <main className="min-h-screen bg-[#0f1117] text-white flex flex-col items-center px-4 pb-24">

      {/* ── Top status badge ── */}
      <div className="w-full max-w-lg pt-4 flex justify-end">
        <span
          className={`text-xs px-3 py-1 rounded-full font-medium ${
            isBackendOnline
              ? "bg-green-900 text-green-400"
              : "bg-red-900 text-red-400"
          }`}
        >
          {isBackendOnline
            ? `● ${backendMode ? backendMode.toUpperCase() : "Backend"} Active`
            : "● Backend Offline"}
        </span>
      </div>

      {/* ── Header ── */}
      <div className="w-full max-w-lg text-center py-8">
        <div className="text-5xl mb-2">🏥</div>
        <h1 className="text-3xl font-bold tracking-tight">
          Ni<span className="text-green-400">Daan</span>
        </h1>
        <p className="text-[#94a3b8] mt-1 text-sm font-noto">
          सही वक्त पर, सही सलाह
        </p>
      </div>

      {/* ── Input card ── */}
      <div className="w-full max-w-lg bg-[#1a1d27] border border-[#2e3347] rounded-2xl p-5">
        <p className="font-semibold text-base mb-1">
          Lakshan Batayein / Describe Symptoms
        </p>
        <p className="text-[#94a3b8] text-sm mb-3 font-noto">
          हिंदी, Hinglish, या English में लिखें
        </p>

        {/* Quick example chips */}
        <div className="flex flex-wrap gap-2 mb-3">
          {[
            { label: "बुखार + दस्त", value: "Bacche ko 2 din se bukhaar hai 38.5°C, dast bhi ho raha hai din mein 4 baar" },
            { label: "शिशु बुखार",  value: "2 mahine ke bacche ko bukhaar hai 38 degree" },
            { label: "सांस की तकलीफ", value: "Patient ko saans lene mein takleef ho rahi hai, chest mein dard hai" },
            { label: "सांप का काटना", value: "Khet mein saanp ne kaata, abhi koi sujan nahi hai" },
          ].map((chip) => (
            <button
              key={chip.label}
              onClick={() => setSymptoms(chip.value)}
              className="text-xs px-3 py-1.5 rounded-full bg-[#22263a] border border-[#2e3347]
                         text-[#94a3b8] hover:border-green-500 hover:text-green-400
                         transition-colors font-noto"
            >
              {chip.label}
            </button>
          ))}
        </div>

        {/* Textarea */}
        <textarea
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
          placeholder="उदाहरण: Bacche ko 2 din se bukhaar hai 38.5°C, dast bhi ho raha hai..."
          rows={5}
          className="w-full bg-[#0f1117] border border-[#2e3347] rounded-xl p-3
                     text-white placeholder-[#475569] text-base resize-none
                     focus:outline-none focus:border-green-500 focus:ring-1
                     focus:ring-green-500 font-noto leading-relaxed"
        />

        {/* Character count */}
        <div className="text-right text-xs text-[#475569] mt-1">
          {symptoms.length} characters
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-3 bg-red-950 border border-red-800 rounded-xl p-3
                          text-red-400 text-sm whitespace-pre-line">
            {error}
          </div>
        )}

        {/* Submit button */}
        <button
          onClick={handleDiagnose}
          disabled={isLoading}
          className="mt-4 w-full bg-green-600 hover:bg-green-500 disabled:bg-green-900
                     disabled:cursor-not-allowed text-white font-semibold text-base
                     py-4 rounded-xl transition-colors flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10"
                  stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor"
                  d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Vishleshan ho raha hai...
            </>
          ) : (
            <>🔍 Jaanch Karein / Diagnose</>
          )}
        </button>
      </div>
    </main>
  );
}