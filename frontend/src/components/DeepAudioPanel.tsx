import type { DeepAudioState } from '../hooks/useDeepAudio';

interface DeepAudioPanelProps {
  state: DeepAudioState;
}

export default function DeepAudioPanel({ state }: DeepAudioPanelProps) {
  const renderNode = (title: string, node: typeof state.acceptance) => {
    if (!node.fileId) return null;

    return (
      <div className="flex-1 bg-black/40 border border-white/10 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-gray-300 mb-3">{title}</h3>

        {node.status === 'idle' && (
          <p className="text-xs text-gray-500">Oczekiwanie na uruchomienie...</p>
        )}

        {node.status === 'processing' && (
          <div className="flex flex-col space-y-2">
            <div className="flex items-center space-x-3 text-blue-400">
              <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              <span className="text-xs font-medium animate-pulse">
                {node.message || 'Przetwarzanie...'}
              </span>
            </div>
            {node.phase && (
              <div className="text-[10px] text-gray-500 uppercase tracking-wide">
                Faza: {node.phase}
              </div>
            )}
          </div>
        )}

        {node.status === 'error' && (
          <div className="bg-red-900/20 text-red-400 text-xs p-3 rounded border border-red-900/50">
            <span className="font-bold">Błąd: </span>{node.error}
          </div>
        )}

        {node.status === 'completed' && (
          <div className="flex flex-col space-y-2">
            <div className="text-green-400 text-xs font-medium flex items-center gap-1.5">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Analiza zakończona
            </div>
            {node.results?.processing_time_seconds && (
              <div className="text-[10px] text-gray-500">
                Czas: {node.results.processing_time_seconds.toFixed(1)}s
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const isVisible = state.acceptance.status !== 'idle' || state.emission.status !== 'idle';

  if (!isVisible) return null;

  return (
    <div className="w-full mt-4 flex flex-col gap-4 p-4 bg-gray-900/50 rounded-xl border border-gray-800">
      <h2 className="text-sm font-bold text-gray-200 uppercase tracking-wider flex items-center gap-2">
        <svg className="w-5 h-5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>
        Status Analizy Deep Audio
      </h2>
      <div className="flex gap-4">
        {renderNode("Acceptance (Video 1)", state.acceptance)}
        {renderNode("Emission (Video 2)", state.emission)}
      </div>
    </div>
  );
}
