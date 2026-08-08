import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

type Lang = "en" | "hi";

interface LanguageContextValue {
  lang: Lang;
  t: (en: string, hi: string) => string;
  toggleLang: () => void;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: "en",
  t: (en) => en,
  toggleLang: () => {},
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => {
    const stored = localStorage.getItem("nidaan-lang");
    return stored === "hi" ? "hi" : "en";
  });

  useEffect(() => {
    document.documentElement.lang = lang;
    localStorage.setItem("nidaan-lang", lang);
  }, [lang]);

  const t = (en: string, hi: string) => (lang === "hi" ? hi : en);
  const toggleLang = () => setLang((l) => (l === "en" ? "hi" : "en"));

  return (
    <LanguageContext.Provider value={{ lang, t, toggleLang }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);