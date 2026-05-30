import { useState } from "react";
import { recommendPHCs } from "../lib/api";
import type { PHCResult, PHCRecommendationRequest } from "../types/nidaan";

export function usePHCRecommend() {
  const [results, setResults] = useState<PHCResult[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const recommend = async (req: PHCRecommendationRequest) => {
    setIsLoading(true);
    setError(null);
    try {
      const trimmedDistrict = req.district.trim();
      if (!trimmedDistrict) {
        throw new Error("District selection required / ज़िला चुनना ज़रूरी है");
      }
      const data = await recommendPHCs({
        ...req,
        district: trimmedDistrict,
      });
      setResults(data);
      if (data.length === 0) {
        setError("Koi PHC nahi mila / इस जिले में कोई PHC नहीं मिला");
      }
    } catch (err: any) {
      console.error("PHC Recommendation error:", err);
      setError(
        err.message || 
        "Network error: Server was unreachable / सर्वर से संपर्क नहीं हो पाया"
      );
    } finally {
      setIsLoading(false);
    }
  };

  return { recommend, isLoading, error, results, setResults };
}
