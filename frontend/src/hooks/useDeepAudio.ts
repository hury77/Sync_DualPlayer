import { useState, useEffect, useRef } from 'react';

export type InstallStatus = 'idle' | 'checking' | 'not_installed' | 'installing' | 'installed' | 'error';
export type AnalysisStatus = 'idle' | 'processing' | 'completed' | 'error';

export interface DeepAudioData {
  stems: {
    vocals: string;
    no_vocals: string;
  };
  transcription: Array<{
    start: number;
    end: number;
    text: string;
  }>;
  processing_time_seconds: number;
}

export interface DeepAudioStateNode {
  fileId: number | null;
  status: AnalysisStatus;
  phase: string | null;
  message: string | null;
  results: DeepAudioData | null;
  error: string | null;
}

export interface DeepAudioState {
  acceptance: DeepAudioStateNode;
  emission: DeepAudioStateNode;
}

const defaultNodeState: DeepAudioStateNode = {
  fileId: null,
  status: 'idle',
  phase: null,
  message: null,
  results: null,
  error: null,
};

export function useDeepAudio() {
  const [installStatus, setInstallStatus] = useState<InstallStatus>('idle');
  const [installProgressMessage, setInstallProgressMessage] = useState<string>('');
  const [installError, setInstallError] = useState<string | null>(null);

  const [deepAudioState, setDeepAudioState] = useState<DeepAudioState>({
    acceptance: { ...defaultNodeState },
    emission: { ...defaultNodeState }
  });
  
  const installPollingRef = useRef<number | null>(null);
  const acceptancePollingRef = useRef<number | null>(null);
  const emissionPollingRef = useRef<number | null>(null);

  const clearInstallPolling = () => {
    if (installPollingRef.current) {
      window.clearInterval(installPollingRef.current);
      installPollingRef.current = null;
    }
  };

  const clearAnalysisPolling = (variant: 'acceptance' | 'emission') => {
    const ref = variant === 'acceptance' ? acceptancePollingRef : emissionPollingRef;
    if (ref.current) {
      window.clearInterval(ref.current);
      ref.current = null;
    }
  };

  const updateNode = (variant: 'acceptance' | 'emission', updates: Partial<DeepAudioStateNode>) => {
    setDeepAudioState(prev => ({
      ...prev,
      [variant]: { ...prev[variant], ...updates }
    }));
  };

  const checkInstallStatus = async () => {
    setInstallStatus('checking');
    try {
      const res = await fetch('/api/v1/deep-audio/install');
      if (res.ok) {
        const data = await res.json();
        setInstallStatus(data.status === 'completed' ? 'installed' : data.status);
        if (data.status === 'installing') {
          setInstallProgressMessage(data.message || 'Instalowanie...');
          startInstallPolling();
        }
      } else {
        setInstallStatus('error');
        setInstallError('Błąd połączenia z serwerem podczas sprawdzania statusu.');
      }
    } catch (e) {
      setInstallStatus('error');
      setInstallError('Nie udało się sprawdzić statusu instalacji.');
    }
  };

  const startInstall = async () => {
    setInstallStatus('installing');
    setInstallProgressMessage('Rozpoczynanie pobierania...');
    setInstallError(null);
    try {
      const res = await fetch('/api/v1/deep-audio/install', { method: 'POST' });
      if (res.ok) {
        startInstallPolling();
      } else {
        const data = await res.json();
        setInstallStatus('error');
        setInstallError(data.detail || 'Błąd instalacji');
      }
    } catch (e) {
      setInstallStatus('error');
      setInstallError('Błąd sieci podczas rozpoczynania instalacji.');
    }
  };

  const startInstallPolling = () => {
    clearInstallPolling();
    installPollingRef.current = window.setInterval(async () => {
      try {
        const res = await fetch('/api/v1/deep-audio/install');
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'completed') {
            setInstallStatus('installed');
            clearInstallPolling();
          } else if (data.status === 'error') {
            setInstallStatus('error');
            setInstallError(data.error || 'Wystąpił błąd podczas instalacji.');
            clearInstallPolling();
          } else {
            setInstallStatus('installing');
            setInstallProgressMessage(data.message || 'Instalowanie...');
          }
        }
      } catch (e) {
        // Zignoruj pojedynczy blad sieci
      }
    }, 2000);
  };

  const startAnalysis = async (acceptanceFileId: number | null, emissionFileId: number | null) => {
    if (!acceptanceFileId && !emissionFileId) {
      updateNode('acceptance', { status: 'error', error: 'Brak ID pliku do analizy.' });
      updateNode('emission', { status: 'error', error: 'Brak ID pliku do analizy.' });
      return;
    }

    if (acceptanceFileId) {
      updateNode('acceptance', { fileId: acceptanceFileId, status: 'processing', message: 'Rozpoczynanie...', error: null, results: null });
      triggerAnalysis(acceptanceFileId, 'acceptance');
    } else {
      updateNode('acceptance', { status: 'error', error: 'Brak ID pliku (oczekiwano synchronizacji z serwerem).' });
    }

    if (emissionFileId) {
      updateNode('emission', { fileId: emissionFileId, status: 'processing', message: 'Oczekiwanie w kolejce...', error: null, results: null });
      triggerAnalysis(emissionFileId, 'emission');
    } else {
      updateNode('emission', { status: 'error', error: 'Brak ID pliku (oczekiwano synchronizacji z serwerem).' });
    }
  };

  const triggerAnalysis = async (fileId: number, variant: 'acceptance' | 'emission') => {
    try {
      const res = await fetch(`/api/v1/files/${fileId}/deep-audio`, { method: 'POST' });
      if (res.ok) {
        startAnalysisPolling(fileId, variant);
      } else {
        const data = await res.json();
        updateNode(variant, { status: 'error', error: data.detail || 'Nie udało się rozpocząć analizy.' });
      }
    } catch (e) {
      updateNode(variant, { status: 'error', error: 'Błąd sieci podczas startu analizy.' });
    }
  };

  const startAnalysisPolling = (fileId: number, variant: 'acceptance' | 'emission') => {
    clearAnalysisPolling(variant);
    const startTime = Date.now();
    const TIMEOUT_MS = 180000;

    const ref = variant === 'acceptance' ? acceptancePollingRef : emissionPollingRef;

    ref.current = window.setInterval(async () => {
      if (Date.now() - startTime > TIMEOUT_MS) {
        updateNode(variant, { status: 'error', error: 'Analiza trwa zbyt długo, przekroczono limit czasu.' });
        clearAnalysisPolling(variant);
        return;
      }

      try {
        const res = await fetch(`/api/v1/files/${fileId}/deep-audio-data`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'completed') {
            updateNode(variant, { status: 'completed', results: data.data, phase: data.phase, message: data.message });
            clearAnalysisPolling(variant);
          } else if (data.status === 'failed') {
            updateNode(variant, { status: 'error', error: data.error || 'Analiza zakończyła się błędem wewnętrznym.', phase: data.phase });
            clearAnalysisPolling(variant);
          } else if (data.status === 'processing') {
            updateNode(variant, { status: 'processing', phase: data.phase, message: data.message || 'Przetwarzanie...' });
          }
        }
      } catch (e) {
        // Ignoruj pomniejsze błędy
      }
    }, 2000);
  };

  useEffect(() => {
    return () => {
      clearInstallPolling();
      clearAnalysisPolling('acceptance');
      clearAnalysisPolling('emission');
    };
  }, []);

  return {
    installStatus,
    installProgressMessage,
    installError,
    checkInstallStatus,
    startInstall,
    setInstallStatus,
    
    deepAudioState,
    startAnalysis,
    setDeepAudioState,
  };
}
