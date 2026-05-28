import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { 
  Trash2, FileText, ChevronRight, Search, SlidersHorizontal, 
  Calendar, AlertCircle, Clock, CheckCircle2, ShieldAlert
} from "lucide-react";
import { useHistory } from "../hooks/useHistory";
import { saveResultToSession } from "../lib/api";
import { formatDate, truncate } from "../lib/utils";
import type { DiagnosisRecord, CriticalityLevel } from "../types/nidaan";

// ─── Severity Color Maps ──────────────────────────────────────────
const SEVERITY_DOT: Record<CriticalityLevel, string> = {
  high: "bg-danger shadow-[0_0_8px_rgba(239,68,68,0.8)]",
  medium: "bg-warning shadow-[0_0_8px_rgba(245,158,11,0.6)]",
  low: "bg-success shadow-[0_0_8px_rgba(16,185,129,0.6)]"
};

const SEVERITY_TEXT: Record<CriticalityLevel, string> = {
  high: "text-danger font-bold",
  medium: "text-warning font-bold",
  low: "text-success font-bold"
};

export default function HistoryPage() {
  const navigate = useNavigate();
  const { records, clearAll } = useHistory();
  const [filter, setFilter] = useState<"all" | CriticalityLevel>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Stats calculation
  const stats = {
    total: records.length,
    high: records.filter(r => r.result?.criticality === "high").length,
    medium: records.filter(r => r.result?.criticality === "medium").length,
    low: records.filter(r => r.result?.criticality === "low").length,
  };

  // Filter & Search records
  const filteredRecords = records.filter(record => {
    const matchesFilter = filter === "all" || record.result?.criticality === filter;
    const matchesSearch = 
      record.symptoms.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (record.result?.reason && record.result.reason.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesFilter && matchesSearch;
  });

  const handleClear = () => {
    if (window.confirm("क्या आप सभी पिछले मामलों को हटाना चाहते हैं?\nAre you sure you want to clear all history? This cannot be undone.")) {
      clearAll();
    }
  };

  const handleView = (record: DiagnosisRecord) => {
    // Save record to session storage so ResultPage loads it correctly
    saveResultToSession(record.symptoms, record.result);
    navigate("/result");
  };

  return (
    <div className="space-y-6">
      
      {/* ── Page Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-display font-extrabold text-2xl text-slate-900 tracking-tight">
            Case History / रिकॉर्ड
          </h2>
          <p className="text-text-secondary text-xs font-noto mt-0.5">ASHA/ANM द्वारा पूर्व में जांचे गए मरीज</p>
        </div>
        {records.length > 0 && (
          <button
            onClick={handleClear}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-100 transition-all cursor-pointer"
            title="Delete all / सब हटाएँ"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">Clear All</span>
          </button>
        )}
      </div>

      {records.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-20 bg-white border border-slate-200/60 rounded-3xl p-6 shadow-xs flex flex-col items-center justify-center"
        >
          <div className="w-20 h-20 bg-slate-50 rounded-2xl flex items-center justify-center mb-4 border border-slate-100">
            <FileText className="w-9 h-9 text-slate-300" />
          </div>
          <h3 className="text-slate-800 font-extrabold text-base mb-1">कोई पिछला मामला नहीं</h3>
          <p className="text-text-muted text-sm max-w-xs mx-auto mb-6">
            No past cases found. Patients you diagnose will appear here for subsequent follow-up.
          </p>
          <button
            onClick={() => navigate("/")}
            className="px-6 py-3 bg-info text-white text-sm font-bold rounded-xl shadow-md hover:bg-info/95 hover:shadow-lg transition-all cursor-pointer"
          >
            मरीज जांच शुरू करें / Diagnose Now
          </button>
        </motion.div>
      ) : (
        <>
          {/* Stats Bar */}
          <div className="grid grid-cols-4 gap-2.5 bg-white border border-slate-200/80 p-3 rounded-2xl shadow-xs">
            <div className="bg-slate-50 border border-slate-100 rounded-xl p-2.5 text-center">
              <span className="block text-lg md:text-xl font-extrabold text-slate-800">{stats.total}</span>
              <span className="text-[10px] font-bold text-text-muted uppercase tracking-wider">Total</span>
            </div>
            <div className="bg-red-50/50 border border-red-100/50 rounded-xl p-2.5 text-center">
              <span className="block text-lg md:text-xl font-extrabold text-danger">{stats.high}</span>
              <span className="text-[10px] font-bold text-danger/80 uppercase tracking-wider">High</span>
            </div>
            <div className="bg-amber-50/50 border border-amber-100/50 rounded-xl p-2.5 text-center">
              <span className="block text-lg md:text-xl font-extrabold text-warning">{stats.medium}</span>
              <span className="text-[10px] font-bold text-warning/80 uppercase tracking-wider">Medium</span>
            </div>
            <div className="bg-emerald-50/50 border border-emerald-100/50 rounded-xl p-2.5 text-center">
              <span className="block text-lg md:text-xl font-extrabold text-success">{stats.low}</span>
              <span className="text-[10px] font-bold text-success/80 uppercase tracking-wider">Low</span>
            </div>
          </div>

          {/* Search and Filters */}
          <div className="space-y-3">
            {/* Search Input */}
            <div className="relative group">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4.5 h-4.5 text-slate-400 group-focus-within:text-info transition-colors" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="लक्षण या निदान से खोजें / Search by symptoms or reasoning..."
                className="w-full bg-white border border-slate-200 rounded-xl py-3 pl-11 pr-4 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:border-info focus:ring-4 focus:ring-info/5 transition-all"
              />
            </div>

            {/* Severity Tabs */}
            <div className="flex gap-1.5 overflow-x-auto no-scrollbar py-1">
              <SlidersHorizontal className="w-4 h-4 text-slate-400 shrink-0 self-center mr-1" />
              {(["all", "high", "medium", "low"] as const).map((type) => (
                <button
                  key={type}
                  onClick={() => setFilter(type)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider whitespace-nowrap transition-all cursor-pointer ${
                    filter === type
                      ? "bg-slate-900 text-white shadow-xs"
                      : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          </div>

          {/* Timeline Style List */}
          <div className="relative pl-6 md:pl-8 border-l border-slate-200 space-y-5 ml-3 md:ml-4 py-1.5">
            <AnimatePresence initial={false}>
              {filteredRecords.map((record, idx) => {
                const criticality = record.result?.criticality || "low";
                return (
                  <motion.div
                    key={record.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.2, delay: idx * 0.05 }}
                    onClick={() => handleView(record)}
                    className="relative bg-white border border-slate-200/80 hover:border-info/40 rounded-2xl p-4 md:p-5 shadow-xs hover:shadow-md transition-all duration-200 cursor-pointer group"
                  >
                    {/* Timeline dot */}
                    <span className={`absolute -left-10 md:-left-12 top-6 w-3 h-3 rounded-full border border-white z-10 ${SEVERITY_DOT[criticality]}`} />
                    
                    <div className="space-y-2.5">
                      {/* Meta header */}
                      <div className="flex items-center justify-between text-xs text-text-muted">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5" />
                          <span>{formatDate(record.timestamp)}</span>
                        </span>
                        <span className="flex items-center gap-1 font-mono text-[10px] bg-slate-100 px-2 py-0.5 rounded border border-slate-200/50">
                          <Clock className="w-3 h-3" />
                          <span>{new Date(record.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </span>
                      </div>

                      {/* Symptoms */}
                      <p className="text-sm font-semibold text-slate-800 line-clamp-2 leading-relaxed font-noto">
                        "{record.symptoms}"
                      </p>

                      {/* Result summary */}
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-slate-100 ${SEVERITY_TEXT[criticality]}`}>
                            {criticality}
                          </span>
                          {record.result?.refer_to_phc ? (
                            <span className="text-[10px] font-bold text-rose-600 bg-rose-50 border border-rose-100 px-1.5 py-0.5 rounded flex items-center gap-1">
                              <ShieldAlert className="w-3 h-3" />
                              <span>PHC Refer</span>
                            </span>
                          ) : (
                            <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 border border-emerald-100 px-1.5 py-0.5 rounded flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" />
                              <span>Home Care</span>
                            </span>
                          )}
                        </div>
                        <span className="text-xs text-info font-bold flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                          <span>Revisit</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </span>
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>

            {filteredRecords.length === 0 && (
              <div className="text-center py-10 text-text-muted text-sm font-medium">
                No past cases matches the filter / search criteria.
              </div>
            )}
          </div>
        </>
      )}

    </div>
  );
}
