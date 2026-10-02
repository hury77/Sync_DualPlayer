import AudioWaveformVisualizer from './AudioWaveformVisualizer';

interface AudioWaveformComparisonProps {
  acceptanceFileId: number | null;
  emissionFileId: number | null;
}

export default function AudioWaveformComparison({ acceptanceFileId, emissionFileId }: AudioWaveformComparisonProps) {
  // Jeśli żaden plik nie ma przypisanego ID (z serwera), nie renderujemy sekcji.
  if (!acceptanceFileId && !emissionFileId) {
    return null;
  }

  return (
    <div className="w-full mt-4 flex flex-col gap-4 p-4 bg-gray-900/50 rounded-xl border border-gray-800">
      <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
        <svg className="w-5 h-5 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
        </svg>
        Waveform Comparison
      </h2>

      <div className="flex flex-col gap-4">
        <AudioWaveformVisualizer fileId={acceptanceFileId} variant="acceptance" />
        <AudioWaveformVisualizer fileId={emissionFileId} variant="emission" />
      </div>
    </div>
  );
}
