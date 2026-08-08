import { useState, useEffect } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";
import { PlusCircle, ClipboardList, MapPin, Info, Activity, X, Moon, Sun } from "lucide-react";
import { cn } from "../../lib/utils";
import { checkHealth } from "../../lib/api";
import { useTheme } from "../../lib/theme";
import { useLanguage } from "../../lib/language";

export default function AppShell() {
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { lang, t, toggleLang } = useLanguage();
  const [isBackendOnline, setIsBackendOnline] = useState(false);
  const [showAbout, setShowAbout] = useState(false);

  // Check backend status on mount and periodically
  useEffect(() => {
    const check = async () => {
      try {
        const health = await checkHealth();
        setIsBackendOnline(true);
      } catch {
        setIsBackendOnline(false);
      }
    };
    check();
    const interval = setInterval(check, 30000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { to: "/", icon: PlusCircle, en: "Diagnose", hi: "जांच करें" },
    { to: "/history", icon: ClipboardList, en: "History", hi: "इतिहास" },
    { to: "/phc", icon: MapPin, en: "PHC Map", hi: "नजदीकी केंद्र" }
  ];

  return (
    <div className="flex flex-col min-h-screen bg-background text-text-primary bg-grid-pattern relative antialiased">
      {/* ── Top Header / Navbar ── */}
      <header className="sticky top-0 z-40 w-full bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-border shadow-sm">
        <div className="max-w-6xl mx-auto h-16 px-4 md:px-8 flex items-center justify-between">
          
          {/* Logo & Title */}
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center">
              <img src="/Nidaan.png" alt="NiDaan" className="w-9 h-9" />
            </div>
            <div>
              <span className="font-display font-extrabold text-xl tracking-tight bg-gradient-to-r from-info to-teal-600 bg-clip-text text-transparent">
                NiDaan
              </span>
            </div>
          </div>

          {/* Desktop Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all duration-200",
                    isActive 
                      ? "bg-info-bg text-info shadow-sm" 
                      : "text-text-secondary hover:text-info hover:bg-slate-100 dark:hover:bg-slate-800"
                  )}
                >
                  <item.icon className="w-4.5 h-4.5" />
                  <span>{t(item.en, item.hi)}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* Right actions: Dark Mode + Language + About + Status */}
          <div className="flex items-center gap-2">
            {/* Language toggle */}
            <button
              onClick={toggleLang}
              className="p-2 rounded-xl text-text-muted hover:text-info hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors font-bold text-sm w-9 h-9 flex items-center justify-center"
              title={lang === "en" ? "Switch to Hindi / हिंदी" : "Switch to English"}
            >
              {lang === "en" ? "हिं" : "EN"}
            </button>
            {/* Dark / Light mode toggle */}
            <button
              onClick={toggleTheme}
              className="p-2 rounded-xl text-text-muted hover:text-info hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title={theme === "dark" ? "Switch to Light Mode" : "Switch to Dark Mode"}
            >
              {theme === "dark"
                ? <Sun className="w-5 h-5" />
                : <Moon className="w-5 h-5" />
              }
            </button>

            {/* About trigger */}
            <button
              onClick={() => setShowAbout(true)}
              className="p-2 rounded-xl text-text-muted hover:text-info hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="About NiDaan / ऐप के बारे में"
            >
              <Info className="w-5 h-5" />
            </button>

            {/* Health check pill */}
            <div
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-semibold shadow-xs select-none transition-all duration-300",
                isBackendOnline
                  ? "bg-success-bg border-success/30 text-success"
                  : "bg-danger-bg border-danger/30 text-danger"
              )}
            >
              <span className={cn(
                "w-1.5 h-1.5 rounded-full",
                isBackendOnline ? "bg-success animate-pulse" : "bg-danger"
              )} />
              <span className="hidden sm:inline">
                {isBackendOnline ? t("AI Engine Online", "AI इंजन ऑनलाइन") : t("AI Engine Offline", "AI इंजन ऑफ़लाइन")}
              </span>
              <span className="sm:hidden">
                {isBackendOnline ? t("ONLINE", "ऑनलाइन") : t("OFFLINE", "ऑफ़लाइन")}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* ── Main Content Area ── */}
      <main className="flex-grow max-w-4xl w-full mx-auto px-4 py-6 md:py-10 pb-28 md:pb-12">
        <Outlet />
      </main>

      {/* ── Mobile Floating Bottom Nav ── */}
      <nav className="md:hidden fixed bottom-5 left-1/2 -translate-x-1/2 w-[90%] max-w-sm h-16 bg-white/90 dark:bg-slate-900/90 backdrop-blur-xl border border-slate-200/80 dark:border-slate-700/80 rounded-2xl flex items-center justify-around z-40 shadow-xl shadow-slate-200/50 dark:shadow-slate-900/50">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to || (item.to !== '/' && location.pathname.startsWith(item.to));
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={cn(
                "flex flex-col items-center justify-center w-full h-full text-text-muted rounded-xl transition-all duration-200",
                isActive && "text-info font-bold"
              )}
            >
              <item.icon className={cn("w-5.5 h-5.5 mb-0.5 transition-transform duration-200", isActive && "scale-110 text-info")} strokeWidth={isActive ? 2.5 : 2} />
              <span className="text-[10px] font-semibold leading-none">{t(item.en, item.hi)}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* ── About NiDaan Modal ── */}
      {showAbout && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
          <div className="relative w-full max-w-md bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-2xl border border-slate-100 dark:border-slate-700 animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => setShowAbout(false)}
              className="absolute top-4 right-4 p-1.5 rounded-full hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-2xl flex items-center justify-center text-xl">
                <img src="/src/assets/Nidaan.png" alt="NiDaan" className="w-14 h-10" />
              </div>
              <div>
                <h3 className="font-display font-extrabold text-lg text-slate-900 dark:text-slate-100">{t("About NiDaan", "NiDaan के बारे में")}</h3>
                <p className="text-xs text-text-muted">{t("AI Diagnostic Assistant for Rural Healthcare", "ग्रामीण स्वास्थ्य सेवा के लिए AI निदान सहायक")}</p>
              </div>
            </div>

            <div className="space-y-3.5 text-sm text-text-secondary">
              <p className="leading-relaxed">
                <strong>NiDaan</strong> {t("is an advanced clinical support system designed specifically for", "एक उन्नत क्लिनिकल सहायता प्रणाली है, जो विशेष रूप से")}
                <strong> {t("ASHA and ANM health workers", "ASHA और ANM स्वास्थ्य कार्यकर्ताओं")} </strong>
                {t("in rural India.", "के लिए बनाई गई है।")}
              </p>
              <p className="leading-relaxed">
                {t("By entering patient symptoms in Hindi, Hinglish, or English, NiDaan uses local", "हिंदी, Hinglish, या English में मरीज के लक्षण दर्ज करने पर NiDaan स्थानीय")} <strong>F-IMNCI</strong>{" "}
                {t("clinical guidelines combined with a local RAG (Retrieval-Augmented Generation) knowledge base to immediately assess criticality.", "क्लिनिकल दिशानिर्देशों और स्थानीय RAG (रेट्रिवल-ऑगमेंटेड जनरेशन) ज्ञान आधार का उपयोग करके तुरंत गंभीरता का आकलन करता है।")}
              </p>
              <div className="p-3.5 rounded-xl bg-info-bg/50 border border-info/10 text-xs dark:text-slate-300 space-y-1">
                <p className="font-bold flex items-center gap-1 text-info">
                  <Activity className="w-4 h-4" /> CLINICAL STANDARDS
                </p>
                <p>{t("• Automatic severity classification (Low, Medium, High)", "• स्वचालित गंभीरता वर्गीकरण (Low, Medium, High)")}</p>
                <p>{t("• Real-time identification of pediatric Red Flags", "• बच्चों के खतरे के लक्षणों (Red Flags) की तुरंत पहचान")}</p>
                <p>{t("• PHC Directory integration for immediate patient referrals", "• तत्काल रेफरल के लिए PHC निर्देशिका एकीकरण")}</p>
              </div>
              <p className="text-xs text-text-muted italic border-t border-slate-100 dark:border-slate-700 pt-3">
                {t("Disclaimer: NiDaan is a diagnostic helper to support decision-making, not a replacement for a qualified professional physician.", "अस्वीकरण: NiDaan निर्णय लेने में सहायता के लिए एक डायग्नोस्टिक सहायक है, यह किसी योग्य पेशेवर चिकित्सक का विकल्प नहीं है।")}
              </p>
            </div>
            
            <button
              onClick={() => setShowAbout(false)}
              className="w-full mt-5 bg-info hover:bg-info/95 text-white font-bold py-3 rounded-xl transition-all shadow-md shadow-info/20"
            >
              {t("Close", "ठीक है")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
