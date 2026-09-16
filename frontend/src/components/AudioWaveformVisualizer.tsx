import React, { useState, useEffect } from 'react';

interface AudioWaveformVisualizerProps {
  fileId: number;
}

export default function AudioWaveformVisualizer({ fileId }: AudioWaveformVisualizerProps) {
  const [status, setStatus] = useState<"processing" | "completed" | "failed">("processing");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    const startTime = Date.now();
    const TIMEOUT_MS = 60000; // 60 sekund

    const checkStatus = async () => {
      if (Date.now() - startTime > TIMEOUT_MS) {
        setStatus("failed");
        setErrorMsg("Analiza trwa zbyt długo, spróbuj ponownie.");
        clearInterval(interval);
        return;
      }

      try {
        const response = await fetch(`/api/v1/files/${fileId}/audio-data`);
        const json = await response.json();
        
        if (json.status === "completed") {
          setStatus("completed");
          setData(json.data);
          clearInterval(interval);
        } else if (json.status === "failed") {
          setStatus("failed");
          setErrorMsg(json.error || "Nieznany błąd podczas analizy audio.");
          clearInterval(interval);
        }
        // jeśli "processing", po prostu czekamy na kolejny cykl
      } catch (err) {
        console.error("Błąd sieci podczas pobierania statusu audio:", err);
      }
    };

    // Odpytanie od razu, potem co 1000ms
    checkStatus();
    interval = setInterval(checkStatus, 1000);

    return () => {
      clearInterval(interval); // cleanup przy odmontowaniu
    };
  }, [fileId]);

  if (status === "processing") {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full bg-black/50 text-white p-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mb-4"></div>
        <p>Analiza Audio...</p>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center w-full h-full bg-red-900/50 text-red-200 p-4 text-center">
        <svg className="w-8 h-8 mb-2 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p className="font-semibold mb-1">Błąd analizy dźwięku</p>
        <p className="text-sm">{errorMsg}</p>
      </div>
    );
  }

  // W tym miejscu znajdzie się docelowe renderowanie waveformu z canvas/svg (STAGE 1D-3)
  return (
    <div className="flex flex-col items-center justify-center w-full h-full bg-[#121212] text-white p-4 border border-white/10 rounded">
      <h3 className="text-lg font-bold mb-2">Wynik Analizy Audio</h3>
      {data?.metrics && (
        <div className="flex gap-4 text-sm mb-4">
          <div className="bg-black/40 px-3 py-1 rounded">LUFS: <span className="font-mono text-blue-400">{data.metrics.lufs}</span></div>
          <div className="bg-black/40 px-3 py-1 rounded">Peak: <span className="font-mono text-red-400">{data.metrics.peak}</span></div>
        </div>
      )}
      <div className="text-xs text-white/50">
        (Wizualizacja Waveform w przygotowaniu - załadowano {data?.waveform?.length || 0} próbek)
      </div>
    </div>
  );
}
