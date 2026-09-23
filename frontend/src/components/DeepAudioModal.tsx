import type { InstallStatus } from '../hooks/useDeepAudio';

interface DeepAudioModalProps {
  isOpen: boolean;
  onClose: () => void;
  onContinue: () => void;
  status: InstallStatus;
  progressMessage: string;
  errorMessage: string | null;
}

export default function DeepAudioModal({
  isOpen,
  onClose,
  onContinue,
  status,
  progressMessage,
  errorMessage
}: DeepAudioModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-[#1e1e1e] border border-[#333] rounded-xl shadow-2xl p-6 max-w-md w-full text-[#e0e0e0]">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white">Deep Audio Analysis</h2>
        </div>

        {status === 'not_installed' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-300">
              Ten moduł wykorzystuje zaawansowane modele sztucznej inteligencji (Whisper i Demucs) do precyzyjnej transkrypcji i separacji ścieżek audio.
            </p>
            <div className="bg-yellow-500/10 border border-yellow-500/20 p-3 rounded-lg text-sm text-yellow-200">
              <strong>Wymagane pobranie modeli (~1.1 GB).</strong><br/>
              Pierwsza analiza na Twoim urządzeniu wymaga pobrania modeli AI i może potrwać do 2 minut.
            </div>
            
            {errorMessage && (
              <div className="bg-red-500/10 border border-red-500/20 p-3 rounded-lg text-sm text-red-400">
                {errorMessage}
              </div>
            )}

            <div className="flex justify-end gap-3 mt-6">
              <button 
                onClick={onClose}
                className="px-4 py-2 rounded-md hover:bg-[#333] text-sm font-medium transition-colors"
              >
                Anuluj
              </button>
              <button 
                onClick={onContinue}
                className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium shadow-lg transition-colors"
              >
                Pobierz i kontynuuj
              </button>
            </div>
          </div>
        )}

        {status === 'installing' && (
          <div className="py-6 flex flex-col items-center justify-center space-y-4">
            <div className="w-10 h-10 border-4 border-[#333] border-t-blue-500 rounded-full animate-spin"></div>
            <p className="text-sm text-gray-300 font-medium">{progressMessage}</p>
          </div>
        )}
        
        {status === 'error' && (
          <div className="space-y-4">
            <div className="bg-red-500/10 border border-red-500/20 p-4 rounded-lg">
              <h3 className="text-red-400 font-semibold mb-2">Błąd instalacji</h3>
              <p className="text-sm text-red-300">{errorMessage || 'Wystąpił nieznany błąd podczas instalacji.'}</p>
            </div>
            <div className="flex justify-end gap-3">
              <button 
                onClick={onClose}
                className="px-4 py-2 rounded-md hover:bg-[#333] text-sm font-medium transition-colors"
              >
                Zamknij
              </button>
              <button 
                onClick={onContinue}
                className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium shadow-lg transition-colors"
              >
                Spróbuj ponownie
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
