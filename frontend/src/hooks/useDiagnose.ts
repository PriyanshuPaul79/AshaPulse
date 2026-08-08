import { useState } from 'react';
import { DiagnosisResult } from '../types/nidaan';

// const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_BASE="https://vasu7-nidaan-backend.hf.space";

const getMockResult = (symptoms: string): DiagnosisResult => {
  const text = symptoms.toLowerCase();
  const isHigh = text.includes('saans') || text.includes('saanp') || text.includes('emergency');
  const isLow = !isHigh && (text.includes('bukhaar') || text.includes('dast') || text.includes('fever'));

  return {
    criticality: isHigh ? 'high' : isLow ? 'low' : 'medium',
    refer_to_phc: isHigh,
    reason: isHigh ? "Symptoms indicate a potentially severe condition requiring immediate medical attention." : "Symptoms are common and can likely be managed at home or closer care.",
    red_flags: isHigh ? ["Rapid breathing", "Possible severe infection"] : [],
    red_flags_in_hindi: isHigh ? ["सांस तेज चलना / सांस फूलना", "गंभीर संक्रमण की संभावना"] : [],
    home_care: !isHigh ? ["Keep the patient hydrated with plenty of fluids", "Ensure proper rest", "Continue feeding appropriate foods"] : [],
    home_care_in_hindi: !isHigh ? ["मरीज को पर्याप्त पानी और तरल पदार्थ दें", "मरीज को उचित आराम दें", "उचित और पौष्टिक आहार देना जारी रखें"] : [],
    medicines: !isHigh ? [
      { name: "Paracetamol", dosage: "1 tablet if fever > 38.5°C", duration: "Up to 3 days" },
      { name: "ORS", dosage: "1 packet mixed in 1L water", duration: "As needed for dehydration" }
    ] : [],
    advice_in_hindi: isHigh 
      ? "यह एक आपातकालीन स्थिति लग रही है। कृपया मरीज को तुरंत नजदीकी प्राथमिक स्वास्थ्य केंद्र (PHC) ले जाएं। बिना डॉक्टर की सलाह के कोई दवा न दें।"
      : "घबराने की कोई बात नहीं है। मरीज को भरपूर आराम दें और तरल पदार्थ पिलाएं। यदि 2 दिन में सुधार न हो, तो डॉक्टर से संपर्क करें।",
    reassess_if_worsens: !isHigh ? ["Fever persists for more than 3 days", "Inability to drink or feed", "Fast or difficult breathing"] : [],
    reassess_if_worsens_in_hindi: !isHigh ? ["बुखार 3 दिन से अधिक समय तक बना रहता है", "मरीज पीने या खाने में असमर्थ है", "सांस तेज चलना या सांस लेने में तकलीफ होना"] : []
  };
};

export function useDiagnose() {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DiagnosisResult | null>(null);

  const diagnose = async (symptoms: string) => {
    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10s for demo

      const response = await fetch(`${API_BASE}/diagnose`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symptoms }),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      if (data.success && data.data) {
        setResult(data.data);
      } else {
        throw new Error(data.error || 'Unknown error from server');
      }
    } catch (err: any) {
      console.warn("Backend fetch failed, using mock data for preview:", err);
      // Fallback to mock data for demonstration
      setTimeout(() => {
        setResult(getMockResult(symptoms));
        setIsLoading(false);
      }, 1500);
      return; // Return early, letting the timeout finish the mock state
    }
    
    setIsLoading(false);
  };

  return { diagnose, isLoading, error, result };
}
