export interface Segment {
  start: number;
  end: number;
  text: string;
}

export interface TranscriptComparisonRow {
  start: number;
  end: number;
  acceptanceText: string | null;
  emissionText: string | null;
  isDifferent: boolean;
  differenceType: 'same' | 'changed' | 'missing_acceptance' | 'missing_emission';
}

function normalize(text: string) {
  return text.toLowerCase().replace(/[^\w\s]|_/g, "").replace(/\s+/g, " ").trim();
}

export function alignTranscripts(
  acceptance: Segment[],
  emission: Segment[],
  tolerance: number = 1.0
): TranscriptComparisonRow[] {
  let i = 0;
  let j = 0;
  const result: TranscriptComparisonRow[] = [];

  const acc = [...acceptance].sort((a,b) => a.start - b.start);
  const emi = [...emission].sort((a,b) => a.start - b.start);

  while (i < acc.length && j < emi.length) {
    const a = acc[i];
    const e = emi[j];

    const overlap = a.start <= e.end && a.end >= e.start;
    const close = Math.abs(a.start - e.start) <= tolerance;

    if (overlap || close) {
      const normA = normalize(a.text);
      const normE = normalize(e.text);
      const isDiff = normA !== normE;

      result.push({
        start: Math.min(a.start, e.start),
        end: Math.max(a.end, e.end),
        acceptanceText: a.text,
        emissionText: e.text,
        isDifferent: isDiff,
        differenceType: isDiff ? 'changed' : 'same'
      });
      i++;
      j++;
    } else if (a.start < e.start) {
      result.push({
        start: a.start,
        end: a.end,
        acceptanceText: a.text,
        emissionText: null,
        isDifferent: true,
        differenceType: 'missing_emission'
      });
      i++;
    } else {
      result.push({
        start: e.start,
        end: e.end,
        acceptanceText: null,
        emissionText: e.text,
        isDifferent: true,
        differenceType: 'missing_acceptance'
      });
      j++;
    }
  }

  while (i < acc.length) {
    const a = acc[i];
    result.push({
      start: a.start,
      end: a.end,
      acceptanceText: a.text,
      emissionText: null,
      isDifferent: true,
      differenceType: 'missing_emission'
    });
    i++;
  }

  while (j < emi.length) {
    const e = emi[j];
    result.push({
      start: e.start,
      end: e.end,
      acceptanceText: null,
      emissionText: e.text,
      isDifferent: true,
      differenceType: 'missing_acceptance'
    });
    j++;
  }

  return result;
}
