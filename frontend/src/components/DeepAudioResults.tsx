import type { AnalysisStatus, DeepAudioData } from '../hooks/useDeepAudio';

interface DeepAudioResultsProps {
  isOpen: boolean;
  onClose: () => void;
  status: AnalysisStatus;
  results: DeepAudioData | null;
  errorMessage: string | null;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

export default function DeepAudioResults({
  isOpen,
  onClose,
  status,
  results,
  errorMessage
}: DeepAudioResultsProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40 transition-opacity"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 w-96 bg-[#1a1a1a] border-l border-[#333] shadow-2xl z-50 flex flex-col transform transition-transform duration-300">
        <div className="flex items-center justify-between p-4 border-b border-[#333]">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-400">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
            Deep Audio Analysis
          </h2>
          <button 
            onClick={onClose}
            className="p-1 rounded-md hover:bg-[#333] text-gray-400 hover:text-white transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M18 6 6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-6">
          {status === 'processing' && (
            <div className="flex flex-col items-center justify-center h-full space-y-4 text-gray-400">
              <div className="w-10 h-10 border-4 border-[#333] border-t-blue-500 rounded-full animate-spin"></div>
              <p className="text-sm font-medium animate-pulse">Analizowanie audio...</p>
              <p className="text-xs text-center px-4">Procesowanie z użyciem modeli AI może potrwać do kilkudziesięciu sekund w zależności od długości pliku.</p>
            </div>
          )}

          {status === 'error' && (
            <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-lg">
              <h3 className="text-red-400 font-semibold mb-2">Błąd analizy</h3>
              <p className="text-sm text-red-300">{errorMessage || 'Analiza zakończyła się niepowodzeniem.'}</p>
            </div>
          )}

          {status === 'completed' && results && (
            <>
              {/* Stems Section */}
              <section>
                <h3 className="text-xs uppercase font-bold text-gray-500 tracking-wider mb-3">Separacja Ścieżek (Demucs)</h3>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-3 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                    <span className="text-lg">🎵</span>
                    <div>
                      <p className="text-sm font-medium text-green-400">Wokale (Acapella)</p>
                      <p className="text-xs text-green-500/70">Wyodrębniono pomyślnie</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 p-3 bg-indigo-500/10 border border-indigo-500/20 rounded-lg">
                    <span className="text-lg">🎸</span>
                    <div>
                      <p className="text-sm font-medium text-indigo-400">Tło muzyczne</p>
                      <p className="text-xs text-indigo-500/70">Wyodrębniono pomyślnie</p>
                    </div>
                  </div>
                </div>
              </section>

              {/* Transcription Section */}
              <section className="flex-1 flex flex-col">
                <h3 className="text-xs uppercase font-bold text-gray-500 tracking-wider mb-3">Transkrypcja (Whisper)</h3>
                <div className="flex-1 space-y-2">
                  {results.transcription.length === 0 ? (
                    <p className="text-sm text-gray-400 italic bg-[#222] p-4 rounded-lg text-center">Brak rozpoznanej mowy w tym pliku.</p>
                  ) : (
                    results.transcription.map((seg, i) => (
                      <div key={i} className="p-3 bg-[#222] rounded-lg border border-[#333] hover:border-gray-600 transition-colors group">
                        <div className="text-[10px] font-mono text-gray-500 mb-1 group-hover:text-blue-400 transition-colors">
                          [{formatTime(seg.start)} - {formatTime(seg.end)}]
                        </div>
                        <p className="text-sm text-gray-200 leading-relaxed">{seg.text}</p>
                      </div>
                    ))
                  )}
                </div>
              </section>

              {/* Telemetry Section */}
              <section className="pt-4 border-t border-[#333] mt-auto">
                <p className="text-xs text-gray-500 text-center flex items-center justify-center gap-2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
                  </svg>
                  Analiza zajęła {results.processing_time_seconds.toFixed(2)} sekund
                </p>
              </section>
            </>
          )}
        </div>
      </div>
    </>
  );
}
