import { describe, it, expect } from 'vitest';
import { alignTranscripts } from './voAlignment';
import type { Segment } from './voAlignment';

describe('voAlignment', () => {
  it('aligns identical segments', () => {
    const acc: Segment[] = [{ start: 0, end: 2, text: "Hello world" }];
    const emi: Segment[] = [{ start: 0, end: 2, text: "Hello world" }];

    const result = alignTranscripts(acc, emi);
    expect(result).toHaveLength(1);
    expect(result[0].differenceType).toBe('same');
    expect(result[0].isDifferent).toBe(false);
  });

  it('detects different text with normalized comparison', () => {
    const acc: Segment[] = [{ start: 0, end: 2, text: "Hello world!" }];
    const emi: Segment[] = [{ start: 0, end: 2, text: "hello, world" }];

    const result = alignTranscripts(acc, emi);
    expect(result[0].differenceType).toBe('same'); // same after normalization
    expect(result[0].isDifferent).toBe(false);
  });

  it('detects actually changed text', () => {
    const acc: Segment[] = [{ start: 0, end: 2, text: "Hello world" }];
    const emi: Segment[] = [{ start: 0, end: 2, text: "Hello friend" }];

    const result = alignTranscripts(acc, emi);
    expect(result[0].differenceType).toBe('changed');
    expect(result[0].isDifferent).toBe(true);
  });

  it('handles missing Acceptance', () => {
    const acc: Segment[] = [];
    const emi: Segment[] = [{ start: 1, end: 3, text: "Only here" }];

    const result = alignTranscripts(acc, emi);
    expect(result).toHaveLength(1);
    expect(result[0].differenceType).toBe('missing_acceptance');
  });

  it('handles missing Emission', () => {
    const acc: Segment[] = [{ start: 1, end: 3, text: "Only here" }];
    const emi: Segment[] = [];

    const result = alignTranscripts(acc, emi);
    expect(result).toHaveLength(1);
    expect(result[0].differenceType).toBe('missing_emission');
  });

  it('aligns segments within tolerance even if timestamps differ', () => {
    const acc: Segment[] = [{ start: 1.0, end: 2.0, text: "Test" }];
    const emi: Segment[] = [{ start: 1.8, end: 2.8, text: "Test" }];

    const result = alignTranscripts(acc, emi);
    expect(result).toHaveLength(1); // They overlap
    expect(result[0].differenceType).toBe('same');
  });

  it('does not align segments outside tolerance (no overlap)', () => {
    const acc: Segment[] = [{ start: 1.0, end: 2.0, text: "A" }];
    const emi: Segment[] = [{ start: 3.5, end: 4.5, text: "B" }];

    const result = alignTranscripts(acc, emi);
    expect(result).toHaveLength(2);
    expect(result[0].differenceType).toBe('missing_emission');
    expect(result[1].differenceType).toBe('missing_acceptance');
  });

  it('keeps chronological order', () => {
    const acc: Segment[] = [
      { start: 3.0, end: 4.0, text: "Second" },
      { start: 1.0, end: 2.0, text: "First" }
    ];
    const emi: Segment[] = [
      { start: 1.0, end: 2.0, text: "First" },
      { start: 3.0, end: 4.0, text: "Second" }
    ];

    const result = alignTranscripts(acc, emi);
    expect(result).toHaveLength(2);
    expect(result[0].acceptanceText).toBe("First");
    expect(result[1].acceptanceText).toBe("Second");
  });
});
