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

export function useDeepAudio() {
  const [installStatus, setInstallStatus] = useState<InstallStatus>('idle');
  const [installProgressMessage, setInstallProgressMessage] = useState<string>('');
  const [installError, setInstallError] = useState<string | null>(null);

  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>('idle');
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [results, setResults] = useState<DeepAudioData | null>(null);
  
  const installPollingRef = useRef<number | null>(null);
  const analysisPollingRef = useRef<number | null>(null);

  const clearInstallPolling = () => {
    if (installPollingRef.current) {
      window.clearInterval(installPollingRef.current);
      installPollingRef.current = null;
    }
  };

  const clearAnalysisPolling = () => {
    if (analysisPollingRef.current) {
      window.clearInterval(analysisPollingRef.current);
      analysisPollingRef.current = null;
    }
  };

  // 1. Sprawdzenie statusu instalacji (na żądanie)
  const checkInstallStatus = async () => {
    setInstallStatus('checking');
    try {
      const res = await fetch('/api/v1/deep-audio/install');
      if (res.ok) {
        const data = await res.json();
        setInstallStatus(data.status);
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

  // 2. Wymuszenie instalacji
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
        // Zignoruj pojedynczy blad sieci podczas pollingu
      }
    }, 2000);
  };

  // 3. Rozpoczęcie analizy audio
  const startAnalysis = async (fileId: number) => {
    setAnalysisStatus('processing');
    setAnalysisError(null);
    setResults(null);
    
    try {
      const res = await fetch(`/api/v1/files/${fileId}/deep-audio`, { method: 'POST' });
      if (res.ok) {
        startAnalysisPolling(fileId);
      } else {
        const data = await res.json();
        setAnalysisStatus('error');
        setAnalysisError(data.detail || 'Nie udało się rozpocząć analizy.');
      }
    } catch (e) {
      setAnalysisStatus('error');
      setAnalysisError('Błąd sieci podczas startu analizy.');
    }
  };

  const startAnalysisPolling = (fileId: number) => {
    clearAnalysisPolling();
    const startTime = Date.now();
    const TIMEOUT_MS = 180000; // 3 minuty timeout dla Whisper + Demucs (kolejkowane)

    analysisPollingRef.current = window.setInterval(async () => {
      if (Date.now() - startTime > TIMEOUT_MS) {
        setAnalysisStatus('error');
        setAnalysisError('Analiza trwa zbyt długo, przekroczono limit czasu.');
        clearAnalysisPolling();
        return;
      }

      try {
        const res = await fetch(`/api/v1/files/${fileId}/deep-audio-data`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === 'completed') {
            setResults(data.data);
            setAnalysisStatus('completed');
            clearAnalysisPolling();
          } else if (data.status === 'failed') {
            setAnalysisStatus('error');
            setAnalysisError(data.error || 'Analiza zakończyła się błędem wewnętrznym.');
            clearAnalysisPolling();
          }
        }
      } catch (e) {
        // Ignoruj pomniejsze błędy połączenia
      }
    }, 2000);
  };

  // Wyczysc pollingi na odmontowanie
  useEffect(() => {
    return () => {
      clearInstallPolling();
      clearAnalysisPolling();
    };
  }, []);

  return {
    installStatus,
    installProgressMessage,
    installError,
    checkInstallStatus,
    startInstall,
    setInstallStatus,
    
    analysisStatus,
    analysisError,
    results,
    startAnalysis,
    setAnalysisStatus,
    clearAnalysisPolling
  };
}
