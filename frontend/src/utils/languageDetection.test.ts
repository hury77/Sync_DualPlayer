import { expect, test, describe } from 'vitest';
import { detectLanguageFromFilename } from './languageDetection';

describe('Language Detection Algorithm', () => {
  test('Returns NONE when no filename is provided', () => {
    const result = detectLanguageFromFilename('', ['Polish']);
    expect(result.confidence).toBe('NONE');
    expect(result.detectedTab).toBeNull();
  });

  test('Returns NONE when no tabs are provided', () => {
    const result = detectLanguageFromFilename('test_PL-PL_video.mp4', []);
    expect(result.confidence).toBe('NONE');
    expect(result.detectedTab).toBeNull();
  });

  describe('Layer 1: ISO Codes', () => {
    test('es-ES matches Spanish (Spain) directly and yields HIGH confidence', () => {
      const result = detectLanguageFromFilename('video_es-ES_promo.mp4', ['Spanish (Spain)', 'English']);
      expect(result.detectedTab).toBe('Spanish (Spain)');
      expect(result.confidence).toBe('HIGH');
      expect(result.tesseractLang).toBe('spa');
    });

    test('PL-PL matches literal PL-PL tab directly and yields HIGH confidence', () => {
      const result = detectLanguageFromFilename('promo_PL-PL_v1.mp4', ['PL-PL', 'EN-US']);
      expect(result.detectedTab).toBe('PL-PL');
      expect(result.confidence).toBe('HIGH');
    });

    test('FR-CA matches French (Canada) directly and yields HIGH confidence', () => {
      const result = detectLanguageFromFilename('promo_fr-ca_v1.mp4', ['French (Canada)', 'French (France)']);
      expect(result.detectedTab).toBe('French (Canada)');
      expect(result.confidence).toBe('HIGH');
    });
    
    test('ISO code matches partially but not exactly -> UNCERTAIN confidence', () => {
      // Intention is "Spanish (Spain)" but available is just "Spanish"
      const result = detectLanguageFromFilename('video_es-ES_promo.mp4', ['Spanish', 'English']);
      expect(result.detectedTab).toBe('Spanish');
      expect(result.confidence).toBe('UNCERTAIN');
    });
  });

  describe('Layer 3: Fallbacks', () => {
    // 1. Test na kolizję kod-kraj vs kod-język:
    test('IT in filename maps to Italian with UNCERTAIN confidence', () => {
      // Consciously handling 2-letter fallback as UNCERTAIN
      const result = detectLanguageFromFilename('promo_IT_video.mp4', ['Italian (Italy)', 'French']);
      expect(result.detectedTab).toBe('Italian (Italy)');
      expect(result.confidence).toBe('UNCERTAIN');
    });

    test('FR in filename maps to French with UNCERTAIN confidence', () => {
      const result = detectLanguageFromFilename('promo_FR_video.mp4', ['French', 'English']);
      expect(result.detectedTab).toBe('French');
      expect(result.confidence).toBe('UNCERTAIN');
    });

    test('ITALY in filename maps to Italian with UNCERTAIN confidence', () => {
      const result = detectLanguageFromFilename('123013_LANCIA_ITALY_TV.mov', ['Italian (Italy)', 'English']);
      expect(result.detectedTab).toBe('Italian (Italy)');
      expect(result.confidence).toBe('UNCERTAIN');
    });

    // 2. Test: fallback bez konkurencji w dokumencie NIE daje HIGH:
    test('Fallback without competition in document STILL yields UNCERTAIN', () => {
      // _FR_ with ONLY one French tab (no competition) -> UNCERTAIN, NOT HIGH.
      const result = detectLanguageFromFilename('video_FR_test.mp4', ['French (France)']);
      expect(result.detectedTab).toBe('French (France)');
      expect(result.confidence).toBe('UNCERTAIN'); // MUST be UNCERTAIN despite no other French tabs
    });
    
    test('HR code with Exact tab match STILL yields UNCERTAIN', () => {
      const result = detectLanguageFromFilename('IHOP_HR_VIDEO.mp4', ['Croatian']);
      expect(result.detectedTab).toBe('Croatian');
      expect(result.confidence).toBe('UNCERTAIN');
    });
  });

  describe('Invariants and Edge Cases', () => {
    // 3. Test na invariant "detectedTab zawsze z availableTabs"
    test('NEVER returns a detectedTab that is not in availableTabs', () => {
      // We detect "Polish" via PL, but the only tab is "German"
      const result = detectLanguageFromFilename('promo_PL_video.mp4', ['German', 'French']);
      expect(result.confidence).toBe('NONE');
      expect(result.detectedTab).toBeNull();
    });

    test('Handles multiple partial matches by picking the first one (but with UNCERTAIN due to Layer 3)', () => {
      // "French" is detected intent via FR. Available: French (Canada), French (France)
      const result = detectLanguageFromFilename('video_FR_test.mp4', ['French (Canada)', 'French (France)']);
      expect(result.detectedTab).toBe('French (Canada)'); // picks the first one
      expect(result.confidence).toBe('UNCERTAIN');
    });

    test('Returns NONE when filename has no discernible language pattern', () => {
      const result = detectLanguageFromFilename('ELX_ProductVideo_Digital_UrbanGreySpeckled.mp4', ['English', 'Polish']);
      expect(result.confidence).toBe('NONE');
      expect(result.detectedTab).toBeNull();
    });
  });
});
