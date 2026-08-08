import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import { MessageSquare, Search, ShieldAlert, Sparkles, Activity, MapPin, Heart } from "lucide-react";
import { diagnose, saveResultToSession } from "../lib/api";
import { useLanguage } from "../lib/language";

const CHIPS = [
  { label: { en: "Fever + Diarrhea", hi: "बुखार + दस्त" }, value: "Bacche ko 2 din se bukhaar hai 38.5°C, dast bhi ho raha hai din mein 4 baar" },
  { label: { en: "Infant Fever", hi: "शिशु बुखार" },   value: "2 mahine ke bacche ko bukhaar hai 38 degree" },
  { label: { en: "Breathing Issue", hi: "सांस तकलीफ" },  value: "Patient ko saans lene mein takleef ho rahi hai, chest mein dard hai" },
  { label: { en: "Snake Bite", hi: "सांप काटना" },   value: "Khet mein saanp ne kaata, abhi koi sujan nahi hai" },
];

export default function HomePage() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [symptoms, setSymptoms] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDiagnose = async () => {
    if (!symptoms.trim()) {
      setError(t("Please enter symptoms", "कृपया लक्षण दर्ज करें"));
      return;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await diagnose(symptoms.trim());
      saveResultToSession(symptoms.trim(), result);
      navigate("/result");
    } catch (err: unknown) {
      if (err instanceof Error) {
        if (err.message.includes("fetch") || err.message.includes("NetworkError")) {
          setError(t("Cannot reach backend on port 8000. Please check the backend.", "सर्वर से जुड़ नहीं पाया। कृपया बैकएंड जांचें।"));
        } else if (err.message.includes("timeout")) {
          setError(t("Analysis timed out. Please try again.", "विश्लेषण में बहुत समय लग रहा है। पुनः प्रयास करें।"));
        } else {
          setError(err.message);
        }
      } else {
        setError(t("An error occurred while analyzing symptoms. Please try again.", "लक्षणों के विश्लेषण में त्रुटि हुई। कृपया पुनः प्रयास करें।"));
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="relative">
      
      {/* ── Hero / Tagline Section ── */}
      <div className="text-center py-4 md:py-6 mb-8">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-info-bg border border-info/10 text-info text-xs font-bold mb-4 shadow-xs"
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span>{t("F-IMNCI Guidelines Enabled", "F-IMNCI दिशानिर्देश सक्रिय")}</span>
        </motion.div>
        
        <motion.h1
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="font-display font-black text-3xl md:text-4xl text-slate-900 dark:text-slate-100 tracking-tight leading-tight"
        >
          {t("AI Diagnostic Assistant for", "ग्रामीण स्वास्थ्य के लिए")} <br />
          <span className="bg-gradient-to-r from-info to-emerald-600 bg-clip-text text-transparent">
            {t("Rural Healthcare", "AI निदान सहायक")}
          </span>
        </motion.h1>
        
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-text-secondary text-sm md:text-base mt-3 max-w-xl mx-auto font-noto px-4 leading-relaxed"
        >
          {t("NiDaan: A fast and reliable decision support for rural health workers (ASHA/ANM)", "निदान: ग्रामीण स्वास्थ्य कार्यकर्ताओं (ASHA/ANM) के लिए त्वरित एवं विश्वसनीय निर्णय सहायक")}
        </motion.p>
      </div>

      {/* ── Main Action Card ── */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.25 }}
        className="bg-white dark:bg-slate-800 border border-slate-200/80 dark:border-slate-700/80 rounded-3xl p-6 md:p-8 shadow-xl shadow-slate-100/70 dark:shadow-slate-900/50"
      >
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-5 bg-info rounded-full" />
            <div>
              <h3 className="font-bold text-slate-800 dark:text-slate-100 text-base md:text-lg">{t("Describe Symptoms", "लक्षण बताएं")}</h3>
              <p className="text-text-muted text-xs font-noto mt-0.5">{t("Type in Hindi, Hinglish, or English", "हिंदी, Hinglish, या English में लिखें")}</p>
            </div>
          </div>
          <span className="text-2xl text-info/80 select-none">🩺</span>
        </div>

        {/* Example Chips */}
        <div className="mb-5">
          <p className="text-xs text-text-secondary font-medium mb-2.5 flex items-center gap-1">
            <MessageSquare className="w-3.5 h-3.5 text-info" />
            <span>{t("Example cases:", "त्वरित उदाहरण:")}</span>
          </p>
          <div className="flex flex-wrap gap-2">
            {CHIPS.map((chip) => (
              <motion.button
                key={chip.label.en}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setSymptoms(chip.value)}
                className="text-xs px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-700 border border-slate-200/60 dark:border-slate-600/60
                           text-slate-700 dark:text-slate-200 hover:border-info/40 hover:bg-info-bg hover:text-info
                           transition-all duration-200 font-noto font-medium"
              >
                {t(chip.label.en, chip.label.hi)}
              </motion.button>
            ))}
          </div>
        </div>

        {/* Input Box Area */}
        <div className="relative mb-5 group">
          <textarea
            value={symptoms}
            onChange={(e) => setSymptoms(e.target.value)}
            placeholder={t("e.g. Child has had high fever for 2 days, trouble breathing, and not eating...", "उदाहरण: बच्चे को 2 दिन से तेज बुखार है, सांस लेने में तकलीफ हो रही है और खाना नहीं खा रहा...")}
            rows={5}
            className="w-full bg-slate-50/50 dark:bg-slate-900/50 border border-slate-200 dark:border-slate-700 rounded-2xl p-4 md:p-5
                       text-slate-800 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 text-sm md:text-base resize-none
                       focus:outline-none focus:bg-white dark:focus:bg-slate-900 focus:border-info focus:ring-4
                       focus:ring-info/5 font-noto leading-relaxed transition-all duration-200"
          />
          
          {/* Action Row Inside Text Area (Char count) */}
          <div className="absolute bottom-4 right-4 flex items-center gap-3">
            {/* Char count */}
            <span className="text-[10px] bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 font-mono px-2 py-1 rounded-md border border-slate-200/50 dark:border-slate-600/50">
              {symptoms.length} chars
            </span>
          </div>
        </div>

        {/* Connection Error Message */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-5 bg-danger-bg border border-danger/20 rounded-2xl p-4 text-danger text-sm flex items-start gap-2.5"
          >
            <ShieldAlert className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <p className="font-bold">{t("Assessment Error", "विश्लेषण में त्रुटि")}</p>
              <p className="text-xs whitespace-pre-line leading-relaxed opacity-90 font-noto">{error}</p>
            </div>
          </motion.div>
        )}

        {/* Submit button */}
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={handleDiagnose}
          disabled={isLoading || !symptoms.trim()}
          className="w-full bg-gradient-to-r from-info to-blue-600 hover:from-info/95 hover:to-blue-700
                     disabled:from-slate-100 disabled:to-slate-100 dark:disabled:from-slate-700 dark:disabled:to-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed
                     text-white font-bold text-base py-4 rounded-2xl shadow-lg shadow-info/10
                     transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer"
        >
          <Search className="w-5 h-5" />
          <span>{t("Run Clinical Assessment", "जांच शुरू करें")}</span>
        </motion.button>
      </motion.div>

      {/* ── Feature highlights grid ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
        <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200/40 dark:border-slate-700/40 rounded-2xl p-4 flex gap-3 items-start">
          <div className="p-2 rounded-xl bg-info-bg text-info">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">{t("Criticality Checks", "गंभीरता जांच")}</h4>
            <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed font-noto">{t("IMNCI-based severity rating (Low, Medium, High) and required care.", "IMNCI आधारित गंभीरता रेटिंग (Low, Medium, High) और आवश्यक उपचार।")}</p>
          </div>
        </div>
        
        <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200/40 dark:border-slate-700/40 rounded-2xl p-4 flex gap-3 items-start">
          <div className="p-2 rounded-xl bg-danger-bg text-danger">
            <Heart className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">{t("Red Flag Detection", "खतरे के लक्षण पहचान")}</h4>
            <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed font-noto">{t("Rapid identification of dangerous signs (Red Flags) in children.", "बच्चों के खतरे के लक्षणों (Red Flags) की त्वरित पहचान।")}</p>
          </div>
        </div>

        <div className="bg-slate-50 dark:bg-slate-800 border border-slate-200/40 dark:border-slate-700/40 rounded-2xl p-4 flex gap-3 items-start">
          <div className="p-2 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
            <MapPin className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">{t("PHC Recommendations", "PHC सिफारिशें")}</h4>
            <p className="text-[11px] text-text-secondary mt-0.5 leading-relaxed font-noto">{t("Mapping of nearest 24x7 active primary health centers with phone contact.", "निकटतम 24x7 सक्रिय प्राथमिक स्वास्थ्य केंद्र की मैपिंग और टेलीफोन संपर्क।")}</p>
          </div>
        </div>
      </div>

      {/* ── LOADING EXPERIENCE OVERLAY ── */}
      <AnimatePresence>
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-md flex items-center justify-center p-4"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 15 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 15 }}
              transition={{ delay: 0.1 }}
              className="bg-white dark:bg-slate-800 rounded-3xl p-6 md:p-10 w-full max-w-md shadow-2xl border border-slate-100 dark:border-slate-700 text-center"
            >
              {/* Medical Pulse Animation */}
              <div className="relative w-24 h-24 mx-auto mb-6 flex items-center justify-center bg-info-bg rounded-full border border-info/10 shadow-inner">
                <span className="absolute inset-0 rounded-full bg-info/10 animate-ping" />
                <span className="absolute inset-2 rounded-full bg-info/15 animate-pulse" />
                <Heart className="w-10 h-10 text-info animate-heartbeat shrink-0" />
              </div>

              <h3 className="text-xl font-display font-extrabold text-slate-900 dark:text-slate-100 mb-2">
                {t("Analyzing Symptoms...", "लक्षणों का विश्लेषण...")}
              </h3>
              <p className="font-noto text-sm text-info font-bold mb-5 tracking-wide">
                {t("Analyzing according to F-IMNCI guidelines...", "F-IMNCI दिशानिर्देशों के अनुसार विश्लेषण हो रहा है...")}
              </p>

              {/* Skeleton loading lines */}
              <div className="space-y-3.5 max-w-xs mx-auto mb-6 opacity-80">
                <div className="h-4 bg-slate-100 dark:bg-slate-700 rounded-full w-full overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-200/60 dark:via-slate-600/60 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
                </div>
                <div className="h-3 bg-slate-100 dark:bg-slate-700 rounded-full w-5/6 overflow-hidden relative mx-auto">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-200/60 dark:via-slate-600/60 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
                </div>
                <div className="h-3 bg-slate-100 dark:bg-slate-700 rounded-full w-4/6 overflow-hidden relative mx-auto">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-slate-200/60 dark:via-slate-600/60 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
                </div>
              </div>

              {/* Guidelines subtext */}
              <div className="p-3 bg-slate-50 dark:bg-slate-700/50 rounded-2xl border border-slate-200/40 dark:border-slate-600/40 text-xs text-text-muted leading-relaxed font-noto">
                {t("Consulting diagnostic RAG database, checking critical symptoms, and mapping local PHC capacities.", "नैदानिक RAG डेटाबेस से परामर्श, खतरनाक लक्षणों की जांच, और स्थानीय PHC क्षमताओं की मैपिंग हो रही है।")}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
      
    </div>
  );
}