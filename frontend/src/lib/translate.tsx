// Central translation helper & Component with free API auto-translation (MyMemory Translation API)

import { useEffect, useState } from "react";

export function isHindiText(text: string): boolean {
  if (!text) return false;
  // Match Devanagari unicode range \u0900-\u097F
  return /[\u0900-\u097F]/.test(text);
}

// In-memory cache for ultra-fast lookups
const API_CACHE: Record<string, string> = {};

// Load persistent cache from localStorage
function getLocalCache(key: string): string | null {
  try {
    return localStorage.getItem(`nidaan_tr_${key}`);
  } catch {
    return null;
  }
}

function setLocalCache(key: string, value: string): void {
  try {
    localStorage.setItem(`nidaan_tr_${key}`, value);
  } catch {}
}

/**
 * Free Translation API call via MyMemory API (No API key required)
 */
export async function translateViaAPI(
  text: string,
  fromLang: "en" | "hi",
  toLang: "en" | "hi"
): Promise<string> {
  const clean = text.trim();
  if (!clean) return "";

  const cacheKey = `${fromLang}_${toLang}_${clean}`;
  if (API_CACHE[cacheKey]) {
    return API_CACHE[cacheKey];
  }

  const stored = getLocalCache(cacheKey);
  if (stored) {
    API_CACHE[cacheKey] = stored;
    return stored;
  }

  try {
    const langpair = `${fromLang}|${toLang}`;
    const url = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(clean)}&langpair=${langpair}`;
    const res = await fetch(url);
    if (res.ok) {
      const json = await res.json();
      const translated = json?.responseData?.translatedText;
      if (translated && typeof translated === "string" && translated.trim().length > 0) {
        const result = translated.trim();
        API_CACHE[cacheKey] = result;
        setLocalCache(cacheKey, result);
        return result;
      }
    }
  } catch (err) {
    console.warn("MyMemory API translation fallback failed:", err);
  }

  return clean;
}

// Hardcoded clinical dictionary for instant offline fallbacks
const CLINICAL_DICTIONARY: Array<{ en: string; hi: string }> = [
  { en: "Keep the patient hydrated with plenty of fluids", hi: "मरीज को पर्याप्त पानी और तरल पदार्थ दें" },
  { en: "Ensure proper rest", hi: "मरीज को पर्याप्त आराम दें" },
  { en: "Continue feeding appropriate foods", hi: "उचित और पौष्टिक आहार देना जारी रखें" },
  { en: "Give ORS solution after each loose stool", hi: "हर पतले दस्त के बाद ORS का घोल दें" },
  { en: "Sponge with lukewarm water for fever", hi: "बुखार होने पर हल्के गुनगुने पानी से पट्टी करें" },
  { en: "Keep patient in a well-ventilated room", hi: "मरीज को हवादार कमरे में रखें" },
  { en: "Continue breastfeeding frequently", hi: "बच्चे को बार-बार स्तनपान कराते रहें" },
  { en: "Give light, soft food like khichdi", hi: "हल्का और सुपाच्य भोजन जैसे खिचड़ी दें" },
  { en: "Monitor body temperature every 4 hours", hi: "हर 4 घंटे में शरीर का तापमान मापें" },
  { en: "Do not give antibiotics without prescription", hi: "डॉक्टर की सलाह के बिना एंटीबायोटिक न दें" },
  { en: "Clean nose with saline drops if blocked", hi: "नाक बंद होने पर सलाइन ड्रॉप्स से साफ करें" },
  { en: "Give zinc supplement daily for 14 days", hi: "14 दिनों तक रोजाना जिंक की गोली दें" },
  { en: "Warm fluids or saline gargles for throat pain", hi: "गले में खराश या दर्द होने पर गर्म तरल पदार्थ या गरारे करें" },
  { en: "Fever persists for more than 3 days", hi: "बुखार 3 दिन से अधिक समय तक बना रहता है" },
  { en: "Inability to drink or feed", hi: "मरीज पीने या खाने में असमर्थ है" },
  { en: "Fast or difficult breathing", hi: "सांस तेज चलना या सांस लेने में तकलीफ होना" },
  { en: "Chest indrawing observed", hi: "छाती धंसना (Chest Indrawing) दिखाई दे" },
  { en: "Persistent vomiting or vomiting everything", hi: "लगातार उल्टी होना या सब कुछ उल्टी कर देना" },
  { en: "Lethargy or unconsciousness", hi: "अत्यधिक सुस्ती, कमजोरी या बेहोशी छाना" },
  { en: "Convulsions or seizures", hi: "दौरे पड़ना या झटके आना" },
  { en: "Blood in stool or vomit", hi: "मल या उल्टी में खून आना" },
  { en: "Condition worsens or new symptoms appear", hi: "स्थिति अधिक बिगड़ने पर या नए लक्षण दिखने पर" },
  { en: "High fever not responding to medication", hi: "दवा देने पर भी तेज बुखार कम न होना" },
  { en: "Rapid breathing", hi: "सांस तेज चलना / सांस फूलना" },
  { en: "Possible severe infection", hi: "गंभीर संक्रमण की संभावना" }
];

/**
 * Synchronous translation check. Returns text instantly if available from 1:1 backend arrays or dictionary.
 */
export function getTranslatedItemSync(
  primaryText: string,
  hindiText?: string,
  lang: "en" | "hi" = "en"
): string {
  const primary = (primaryText || "").trim();
  const hindi = (hindiText || "").trim();

  if (!primary && !hindi) return "";

  if (lang === "en") {
    if (primary && !isHindiText(primary)) return primary;
    if (hindi && !isHindiText(hindi)) return hindi;

    const hindiSource = isHindiText(primary) ? primary : hindi;
    if (hindiSource) {
      for (const item of CLINICAL_DICTIONARY) {
        if (item.hi.trim() === hindiSource) return item.en;
      }
    }
    return primary || hindi;
  } else {
    if (hindi && isHindiText(hindi)) return hindi;
    if (primary && isHindiText(primary)) return primary;

    if (primary) {
      const lower = primary.toLowerCase();
      for (const item of CLINICAL_DICTIONARY) {
        if (item.en.toLowerCase() === lower) return item.hi;
      }
      for (const item of CLINICAL_DICTIONARY) {
        if (lower.includes(item.en.toLowerCase()) || item.en.toLowerCase().includes(lower)) return item.hi;
      }
    }
    return hindi || primary;
  }
}

/**
 * React Component for dynamic translation using MyMemory Free Translation API + Local Caching.
 * Automatically translates English <-> Hindi in real-time when toggled.
 */
export function TranslatedText({
  text,
  hindiText,
  lang,
  className = ""
}: {
  text: string;
  hindiText?: string;
  lang: "en" | "hi";
  className?: string;
}) {
  const [displayText, setDisplayText] = useState(() =>
    getTranslatedItemSync(text, hindiText, lang)
  );

  useEffect(() => {
    let isMounted = true;
    const syncResult = getTranslatedItemSync(text, hindiText, lang);
    setDisplayText(syncResult);

    // If Hindi mode is requested but the result is still English, or English mode requested but result is Hindi, call Free API
    const needsApi =
      (lang === "hi" && !isHindiText(syncResult)) ||
      (lang === "en" && isHindiText(syncResult));

    if (needsApi) {
      const sourceText = lang === "hi" ? text : (hindiText || text);
      const from = lang === "hi" ? "en" : "hi";
      const to = lang === "hi" ? "hi" : "en";

      translateViaAPI(sourceText, from, to).then((resText) => {
        if (isMounted && resText) {
          setDisplayText(resText);
        }
      });
    }

    return () => {
      isMounted = false;
    };
  }, [text, hindiText, lang]);

  return <span className={className}>{displayText}</span>;
}

// Backward compatible export function alias
export const getTranslatedItem = getTranslatedItemSync;
