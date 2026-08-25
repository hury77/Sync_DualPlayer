export type ConfidenceLevel = 'HIGH' | 'UNCERTAIN' | 'NONE';

export interface LanguageMatchResult {
  detectedTab: string | null;
  tesseractLang: string | null;
  confidence: ConfidenceLevel;
  reason?: string;
}

// Map literal tab names to Tesseract engine codes
export const LANGUAGE_TO_TESSERACT: Record<string, string> = {
  "English": "eng",
  "English (US)": "eng",
  "United Kingdom": "eng",
  "Arabic": "ara",
  "Chinese (Simplified)": "chi_sim",
  "Chinese (Traditional)": "chi_tra",
  "HONG KONG": "chi_tra",
  "Croatian": "hrv",
  "Czech": "ces",
  "Danish": "dan",
  "Dutch": "nld",
  "Finnish": "fin",
  "French": "fra",
  "French (Canada)": "fra",
  "French (France,Benelux)": "fra",
  "German": "deu",
  "German (Germany, Austria, Switzerland)": "deu",
  "Greek": "ell",
  "Hungarian": "hun",
  "Italian (Italy)": "ita",
  "Italian": "ita",
  "Korean": "kor",
  "Norwegian": "nor",
  "Polish": "pol",
  "Portuguese (Brazil)": "por",
  "Portuguese (Portugal)": "por",
  "Romanian": "ron",
  "Spanish (Latin America)": "spa",
  "Spanish (Spain)": "spa",
  "Spanish": "spa",
  "Swedish": "swe",
  "Turkish": "tur",
  "Japanese": "jpn",
  "Russian": "rus",
};

// Layer 1: ISO Codes -> Generic Name or Specific Name Intention
const ISO_MAP: Record<string, string> = {
  "PL-PL": "Polish",
  "EN-US": "English", 
  "EN-GB": "United Kingdom",
  "ES-ES": "Spanish (Spain)",
  "ES-CO": "Spanish (Latin America)",
  "ES-MX": "Spanish (Latin America)",
  "FR-CA": "French (Canada)",
  "FR-FR": "French (France,Benelux)",
  "DE-DE": "German (Germany, Austria, Switzerland)",
  "IT-IT": "Italian (Italy)",
  "PT-BR": "Portuguese (Brazil)",
  "PT-PT": "Portuguese (Portugal)",
  "CN-SC": "Chinese (Simplified)",
  "TW-TC": "Chinese (Traditional)",
  "HK-TC": "HONG KONG",
  "AR-AE": "Arabic",
};

// Layer 3: Fallback Two-Letter Codes -> Generic Name
const FALLBACK_CODE_MAP: Record<string, string> = {
  "PL": "Polish",
  "EN": "English",
  "US": "English",
  "UK": "United Kingdom",
  "HR": "Croatian",
  "AR": "Arabic",
  "CN": "Chinese (Simplified)",
  "ZH": "Chinese (Simplified)",
  "TW": "Chinese (Traditional)",
  "HK": "HONG KONG",
  "FR": "French",
  "DE": "German",
  "IT": "Italian",
  "ES": "Spanish",
  "PT": "Portuguese",
  "NL": "Dutch",
  "FI": "Finnish",
  "DK": "Danish",
  "NO": "Norwegian",
  "SE": "Swedish",
  "SV": "Swedish",
  "CZ": "Czech",
  "GR": "Greek",
  "HU": "Hungarian",
  "RO": "Romanian",
  "TR": "Turkish",
  "JP": "Japanese",
  "JA": "Japanese",
  "KR": "Korean",
  "KO": "Korean",
  "RU": "Russian"
};

const COUNTRY_MAP: Record<string, string> = {
  "ITALY": "Italian",
  "GERMANY": "German",
  "FRANCE": "French",
  "SPAIN": "Spanish",
  "POLAND": "Polish",
  "CZECH": "Czech",
  "BRAZIL": "Portuguese (Brazil)",
  "CANADA": "French (Canada)"
};

export function detectLanguageFromFilename(filename: string, availableTabs: string[]): LanguageMatchResult {
  if (!filename) return { detectedTab: null, tesseractLang: null, confidence: 'NONE' };
  
  if (!availableTabs || availableTabs.length === 0) {
      return { detectedTab: null, tesseractLang: null, confidence: 'NONE', reason: 'No tabs provided' };
  }

  let detectedIntent: string | null = null;
  let layer: 1 | 3 | null = null;

  // 1. Layer 1: ISO Code Match (XX-XX)
  const isoMatch = filename.match(/[_-]([a-zA-Z]{2}[-_][a-zA-Z]{2})[_-]/);
  if (isoMatch) {
    const code = isoMatch[1].replace('_', '-').toUpperCase();
    
    // Direct match if ISO code itself is a tab (like "PL-PL" in new_brief.xlsx)
    const directTabMatch = availableTabs.find(t => t.toUpperCase() === code);
    if (directTabMatch) {
       detectedIntent = directTabMatch;
       layer = 1;
    } else if (ISO_MAP[code]) {
      detectedIntent = ISO_MAP[code];
      layer = 1;
    }
  }

  // 2. Layer 3: Fallback country names (e.g. ITALY)
  if (!layer) {
    for (const [country, lang] of Object.entries(COUNTRY_MAP)) {
      if (filename.toUpperCase().includes(country)) {
        detectedIntent = lang;
        layer = 3;
        break;
      }
    }
  }

  // 3. Layer 3: Fallback 2-letter codes (e.g. HR, FR, IT)
  if (!layer) {
    const codeMatch = filename.match(/[_-]([a-zA-Z]{2})[_-]/);
    if (codeMatch) {
      const code = codeMatch[1].toUpperCase();
      if (FALLBACK_CODE_MAP[code]) {
        detectedIntent = FALLBACK_CODE_MAP[code];
        layer = 3;
      }
    }
  }

  if (!detectedIntent) {
    return { detectedTab: null, tesseractLang: null, confidence: 'NONE', reason: 'No pattern matched' };
  }

  let bestTab: string | null = null;
  
  // Exact match
  const exactMatch = availableTabs.find(t => t.toLowerCase() === detectedIntent!.toLowerCase());
  
  if (exactMatch) {
    bestTab = exactMatch;
  } else {
    // Partial match: find tabs that contain the intent, or intent contains the tab
    const partialMatches = availableTabs.filter(t => 
      t.toLowerCase().includes(detectedIntent!.toLowerCase()) || 
      detectedIntent!.toLowerCase().includes(t.toLowerCase())
    );
    if (partialMatches.length > 0) {
      bestTab = partialMatches[0];
    }
  }

  // Invariant: NEVER return a tab that is not in availableTabs
  if (!bestTab) {
    return { detectedTab: null, tesseractLang: null, confidence: 'NONE', reason: 'Intent matched but no corresponding tab found' };
  }

  // Rule: Confidence MUST depend on the layer that matched
  // - Layer 1 + Exact match -> HIGH
  // - Layer 3 (Fallback) -> ALWAYS UNCERTAIN (even if no competition in document)
  let confidence: ConfidenceLevel = 'UNCERTAIN';
  if (layer === 1 && exactMatch) {
     confidence = 'HIGH';
  }

  const tesseractLang = LANGUAGE_TO_TESSERACT[bestTab] || LANGUAGE_TO_TESSERACT[detectedIntent] || null;

  return {
    detectedTab: bestTab, // Guarantees returning an element from availableTabs or null
    tesseractLang,
    confidence
  };
}
