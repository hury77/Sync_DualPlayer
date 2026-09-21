import { useState, useEffect, useRef } from 'react';

interface AudioWaveformVisualizerProps {
  fileId: number;
  variant: "acceptance" | "emission";
}

export default function AudioWaveformVisualizer({ fileId, variant }: AudioWaveformVisualizerProps) {
  const [status, setStatus] = useState<"processing" | "completed" | "failed">("processing");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [data, setData] = useState<any>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let interval: ReturnType<typeof setTimeout>;
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
      } catch (err) {
        console.error("Błąd sieci podczas pobierania statusu audio:", err);
      }
    };

    checkStatus();
    interval = setInterval(checkStatus, 1000);

    return () => {
      clearInterval(interval);
    };
  }, [fileId]);

  useEffect(() => {
    if (status === "completed" && data?.waveform && canvasRef.current) {
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const width = canvas.width;
      const height = canvas.height;
      
      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Set styles based on variant
      const isAcceptance = variant === "acceptance";
      ctx.fillStyle = isAcceptance ? '#3b82f6' : '#ef4444'; // blue-500 or red-500
      
      const waveform: number[] = data.waveform;
      const pointWidth = width / waveform.length;
      const center = height / 2;

      // Draw middle line
      ctx.beginPath();
      ctx.moveTo(0, center);
      ctx.lineTo(width, center);
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.stroke();

      // Draw waveform bars
      waveform.forEach((val, i) => {
        // val is 0.0 to 1.0 peak
        const barHeight = Math.max(val * height, 1);
        const x = i * pointWidth;
        const y = center - barHeight / 2;
        
        ctx.fillRect(x, y, pointWidth, barHeight);
      });
    }
  }, [status, data, variant]);

  if (status === "processing") {
    return (
      <div className="flex flex-col items-center justify-center w-full h-[60vh] bg-black/50 text-white p-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mb-4"></div>
        <p>Analiza Audio...</p>
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center w-full h-[60vh] bg-red-900/50 text-red-200 p-4 text-center">
        <svg className="w-8 h-8 mb-2 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p className="font-semibold mb-1">Błąd analizy dźwięku</p>
        <p className="text-sm">{errorMsg}</p>
      </div>
    );
  }

  const bgColor = variant === "acceptance" ? "bg-blue-900/20 border-blue-500/30" : "bg-red-900/20 border-red-500/30";
  const titleColor = variant === "acceptance" ? "text-blue-400" : "text-red-400";
  const title = variant === "acceptance" ? "Acceptance Waveform" : "Emission Waveform";

  return (
    <div className={`flex flex-col items-center w-full h-[60vh] text-white p-4 border rounded relative overflow-hidden ${bgColor}`}>
      <div className="flex justify-between items-center w-full mb-2">
        <h3 className={`text-sm font-bold uppercase tracking-wider ${titleColor}`}>{title}</h3>
        {data?.metrics && (
          <div className="flex gap-4 text-xs font-mono">
            <div className="bg-black/40 px-2 py-1 rounded">LUFS: <span className="text-white">{data.metrics.lufs}</span></div>
            <div className="bg-black/40 px-2 py-1 rounded">Peak: <span className="text-white">{data.metrics.peak}</span></div>
          </div>
        )}
      </div>
      
      <div className="flex-1 w-full bg-black/60 rounded overflow-hidden relative shadow-inner">
        <canvas 
          ref={canvasRef}
          width={1000}
          height={300}
          className="w-full h-full object-cover"
        />
      </div>
    </div>
  );
}
