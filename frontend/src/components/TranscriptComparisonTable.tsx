import { useState, useMemo } from 'react';
import type { DeepAudioState } from '../hooks/useDeepAudio';
import { alignTranscripts } from '../utils/voAlignment';
import type { Segment, TranscriptComparisonRow } from '../utils/voAlignment';

interface TranscriptComparisonTableProps {
  state: DeepAudioState;
}

export default function TranscriptComparisonTable({ state }: TranscriptComparisonTableProps) {
  const [isExporting, setIsExporting] = useState(false);

  const accState = state.acceptance;
  const emState = state.emission;

  const rows = useMemo(() => {
    // Tabela jest widoczna i generuje dane nawet, jeśli jedna strona ma error lub processing.
    // Używamy tylko `completed` jako bazy do wyrównywania.
    const accSegments: Segment[] = accState.status === 'completed' && accState.results?.transcription
      ? accState.results.transcription
      : [];

    const emSegments: Segment[] = emState.status === 'completed' && emState.results?.transcription
      ? emState.results.transcription
      : [];

    return alignTranscripts(accSegments, emSegments);
  }, [accState, emState]);

  const hasData = rows.length > 0;
  const isVisible = accState.status !== 'idle' || emState.status !== 'idle';

  if (!isVisible) return null;

  const handleExport = async () => {
    if (!hasData) return;
    setIsExporting(true);

    try {
      const response = await fetch('/api/v1/files/export-vo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rows)
      });

      if (!response.ok) throw new Error('Błąd eksportu');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `vo_comparison_${Date.now()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error(err);
      alert('Nie udało się wyeksportować pliku XLSX.');
    } finally {
      setIsExporting(false);
    }
  };

  const renderStatus = (row: TranscriptComparisonRow) => {
    if (row.differenceType === 'same') return <span className="text-green-400 font-bold">Identical</span>;
    if (row.differenceType === 'changed') return <span className="text-red-400 font-bold">Different</span>;
    if (row.differenceType === 'missing_emission') return <span className="text-red-400 font-bold">Missing Emission</span>;
    if (row.differenceType === 'missing_acceptance') return <span className="text-red-400 font-bold">Missing Acceptance</span>;
    return null;
  };

  const getRowClass = (diff: string) => {
    return diff === 'same' ? 'hover:bg-gray-800' : 'bg-red-950/20 hover:bg-red-900/30';
  };

  const getCellClass = (text: string | null, isMissing: boolean) => {
    if (isMissing) return 'bg-red-900/40 text-red-300 font-medium italic';
    if (!text) return 'text-gray-500 italic';
    return 'text-gray-200';
  };

  return (
    <div className="w-full mt-4 flex flex-col gap-4 p-4 bg-gray-900/50 rounded-xl border border-gray-800">
      <div className="flex justify-between items-center w-full">
        <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
          <svg className="w-5 h-5 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Transcript Comparison
        </h2>

        <button
          onClick={handleExport}
          disabled={!hasData || isExporting}
          className="px-4 py-1.5 text-xs font-semibold rounded-md transition-colors text-white bg-green-600 hover:bg-green-500 shadow-sm border border-green-400/50 disabled:bg-gray-700 disabled:border-gray-600 disabled:opacity-50"
        >
          {isExporting ? 'Exporting...' : 'Export Excel'}
        </button>
      </div>

      <div className="overflow-x-auto w-full bg-black/40 rounded border border-gray-700">
        <table className="w-full text-sm text-left">
          <thead className="text-xs uppercase bg-gray-800 text-gray-300">
            <tr>
              <th className="px-4 py-3 w-32 border-b border-gray-700">Time</th>
              <th className="px-4 py-3 w-1/3 border-b border-l border-gray-700 text-blue-400">Acceptance VO</th>
              <th className="px-4 py-3 w-1/3 border-b border-l border-gray-700 text-red-400">Emission VO</th>
              <th className="px-4 py-3 border-b border-l border-gray-700">Difference</th>
            </tr>
          </thead>
          <tbody>
            {!hasData ? (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-gray-500 italic">
                  Brak danych transkrypcji (poczekaj na analizę lub wgraj pliki).
                </td>
              </tr>
            ) : (
              rows.map((row, idx) => (
                <tr key={idx} className={`border-b border-gray-800 transition-colors ${getRowClass(row.differenceType)}`}>
                  <td className="px-4 py-3 text-gray-400 font-mono text-xs whitespace-nowrap">
                    {row.start.toFixed(1)}s - {row.end.toFixed(1)}s
                  </td>
                  <td className={`px-4 py-3 border-l border-gray-800 ${getCellClass(row.acceptanceText, row.differenceType === 'missing_acceptance')}`}>
                    {row.differenceType === 'missing_acceptance' ? 'BRAK' : (row.acceptanceText || '-')}
                  </td>
                  <td className={`px-4 py-3 border-l border-gray-800 ${getCellClass(row.emissionText, row.differenceType === 'missing_emission')}`}>
                    {row.differenceType === 'missing_emission' ? 'BRAK' : (row.emissionText || '-')}
                  </td>
                  <td className="px-4 py-3 border-l border-gray-800">
                    {renderStatus(row)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
