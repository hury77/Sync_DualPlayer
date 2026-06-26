import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  PlayIcon,
  PauseIcon,
  StopIcon,
  ArrowPathIcon,
  XMarkIcon,
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ArrowUpTrayIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  EyeIcon,
  EyeSlashIcon,
  CameraIcon,
  EyeDropperIcon,
  DocumentTextIcon,
} from "@heroicons/react/24/outline";
import Tesseract from "tesseract.js";
import { diffWords, diffChars } from "diff";
import { jsPDF } from "jspdf";
import html2canvas from "html2canvas";

const RulerIcon = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 4.5l-15 15m0 0l-3-3 15-15 3 3-15 15z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 7.5l1.5 1.5M13.5 10.5l1.5 1.5M10.5 13.5l1.5 1.5M7.5 16.5l1.5 1.5" />
  </svg>
);

interface RulerLine {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
  sourceVideo: "acceptance" | "emission";
  color: string;
}

interface VideoFile {
  url: string;
  name: string;
  size: number;
  isLocal: boolean; // True if using URL.createObjectURL, false if streamed from backend
  fileId?: number;  // Optional, if uploaded to backend
  conversionTime?: number; // Optional, time took to transcode
}


interface ReportItem {
  id: string;
  timecode: number;
  type: "visual" | "ocr" | "unified" | "single";
  comment: string;
  acceptanceImage?: string;
  emissionImage?: string;
  diffImage?: string;
  ocrPanelImage?: string;
  ocrTextAcceptance?: string;
  ocrTextEmission?: string;
  ocrBriefText?: string;
}

const LANGUAGE_TO_TESSERACT: Record<string, string> = {
  "Arabic": "ara",
  "Chinese (Simplified)": "chi_sim",
  "Chinese (Traditional)": "chi_tra",
  "Croatian": "hrv",
  "Czech": "ces",
  "Danish": "dan",
  "Dutch": "nld",
  "English": "eng",
  "English (UK/ANZ/UAE/ASIA)": "eng",
  "Finnish": "fin",
  "French": "fra",
  "French (Canada)": "fra",
  "French (France)": "fra",
  "German": "deu",
  "German (Germany)": "deu",
  "Greek": "ell",
  "Hungarian": "hun",
  "Italian": "ita",
  "Japanese": "jpn",
  "Korean": "kor",
  "Norwegian": "nor",
  "Polish": "pol",
  "Portuguese": "por",
  "Portuguese (Brazil)": "por",
  "Romanian": "ron",
  "Russian": "rus",
  "Spanish": "spa",
  "Spanish (Latin America)": "spa",
  "Spanish (Spain)": "spa",
  "Swedish": "swe",
  "Turkish": "tur",
};

const normalizeTextForDiff = (text: string) => {
  if (!text) return "";
  return text
    .replace(/\r/g, "") // Usuń carriage returns z Windows/Excel
    .split("\n")
    .map(line => line.trimEnd()) // Usuń białe znaki na końcu każdej linii
    .join("\n")
    .trim(); // Usuń białe znaki na początku i końcu całego tekstu
};

const getBoundedDimensions = (vw: number, vh: number, maxW = 1280, maxH = 1280) => {
  if (!vw || !vh) return { w: maxW, h: maxH };
  let scale = 1;
  if (vw > maxW || vh > maxH) {
    scale = Math.min(maxW / vw, maxH / vh);
  }
  return { w: Math.round(vw * scale), h: Math.round(vh * scale) };
};

export const SyncDualPlayer: React.FC = () => {
  const [acceptanceFile, setAcceptanceFile] = useState<VideoFile | null>(null);
  const [emissionFile, setEmissionFile] = useState<VideoFile | null>(null);

  // Resolution States
  const [accDimensions, setAccDimensions] = useState<{width: number, height: number} | null>(null);
  const [emDimensions, setEmDimensions] = useState<{width: number, height: number} | null>(null);

  // Eyedropper States
  const [isEyedropperActive, setIsEyedropperActive] = useState(false);
  const [hoverColor, setHoverColor] = useState<{ r: number, g: number, b: number, hex: string, x: number, y: number, sourceX: number, sourceY: number, sourceVideo: "acceptance" | "emission" } | null>(null);
  const [eyedropperDrops, setEyedropperDrops] = useState<{ r: number, g: number, b: number, hex: string, sourceX: number, sourceY: number, sourceVideo: "acceptance" | "emission" }[]>([]);

  // Ruler States
  const [isRulerActive, setIsRulerActive] = useState(false);
  const [rulerColor, setRulerColor] = useState("#3b82f6");
  const [rulerLines, setRulerLines] = useState<RulerLine[]>([]);
  const [activeRulerLine, setActiveRulerLine] = useState<RulerLine | null>(null);

  // OCR / Compare Copy States
  const [isOcrActive, setIsOcrActive] = useState(false);
  const [ocrLanguage, setOcrLanguage] = useState("eng+pol"); // default to multi-language
  const [ocrCustomLanguage, setOcrCustomLanguage] = useState("");
  const [ocrInvertColors, setOcrInvertColors] = useState(false);
  const [ocrBoxAcceptance, setOcrBoxAcceptance] = useState<{startX: number, startY: number, endX: number, endY: number} | null>(null);
  const [ocrBoxEmission, setOcrBoxEmission] = useState<{startX: number, startY: number, endX: number, endY: number} | null>(null);
  const [activeOcrBox, setActiveOcrBox] = useState<{startX: number, startY: number, endX: number, endY: number, sourceVideo: "acceptance" | "emission"} | null>(null);
  const [ocrTextAcceptance, setOcrTextAcceptance] = useState("");
  const [ocrTextEmission, setOcrTextEmission] = useState("");
  const [ocrBriefText, setOcrBriefText] = useState("");
  const [availableCopydeckLines, setAvailableCopydeckLines] = useState<string[]>([]);
  const [isOcrProcessing, setIsOcrProcessing] = useState(false);
  const [ocrProgressMessage, setOcrProgressMessage] = useState("");
  const [ocrContrast, setOcrContrast] = useState(80);
  const [ocrPreviewAcceptance, setOcrPreviewAcceptance] = useState<string | null>(null);
  const [ocrPreviewEmission, setOcrPreviewEmission] = useState<string | null>(null);

  // Report Builder State
  const [reportItems, setReportItems] = useState<ReportItem[]>([]);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [capturingReport, setCapturingReport] = useState(false);
  const [pendingReportItem, setPendingReportItem] = useState<ReportItem | null>(null);

  // Trim States
  const [acceptanceTrim, setAcceptanceTrim] = useState(0);
  const [emissionTrim, setEmissionTrim] = useState(0);

  // Loading/Transcoding States for Backend MXF/MOV Path
  const [acceptanceLoading, setAcceptanceLoading] = useState(false);
  const [emissionLoading, setEmissionLoading] = useState(false);
  const [acceptanceLoadingMessage, setAcceptanceLoadingMessage] = useState("");
  const [emissionLoadingMessage, setEmissionLoadingMessage] = useState("");
  const [acceptanceProgress, setAcceptanceProgress] = useState<number | null>(null);
  const [emissionProgress, setEmissionProgress] = useState<number | null>(null);
  const [acceptanceError, setAcceptanceError] = useState<string | null>(null);
  const [emissionError, setEmissionError] = useState<string | null>(null);

  // Active polling refs to manage async timeouts and prevent memory leaks
  const activePollsRef = useRef<{ acceptance?: ReturnType<typeof setTimeout>; emission?: ReturnType<typeof setTimeout> }>({});

  // Playback States
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [acceptanceVolume, setAcceptanceVolume] = useState(1);
  const [emissionVolume, setEmissionVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  // Drag-and-drop highlighting states
  const [isDraggingAcceptance, setIsDraggingAcceptance] = useState(false);
  const [isDraggingEmission, setIsDraggingEmission] = useState(false);

  // ── Diff Overlay State ────────────────────────────────────────────────────
  const [diffMode, setDiffMode] = useState(false);
  const [wipePosition, setWipePosition] = useState(50); // 0-100%
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [diffTimestamps, setDiffTimestamps] = useState<
    { time: number; severity: "certain" | "review" }[]
  >([]);
  const [screenshotSaving, setScreenshotSaving] = useState(false);

  // ── Single Player Mode State ────────────────────────────────────────────────
  const [isSinglePlayerMode, setIsSinglePlayerMode] = useState(false);

  

  // ── Playstation QA State ─────────────────────────────────────────────
  const [psQaResults, setPsQaResults] = useState<{
    rating: string, 
    bing: string, 
    bong: string, 
    expected_rating_b64?: string | null,
    expected_bing_b64?: string | null,
    expected_bong_b64?: string | null,
    scanTime?: string
  } | null>(null);
  const [isPsQaAnalyzing, setIsPsQaAnalyzing] = useState(false);
  const [psQaMetadata, setPsQaMetadata] = useState<{country: string, rating: string, bing: string, bong: string} | null>(null);

  // ── Copydeck State ───────────────────────────────────────────────────
  const [copydeckData, setCopydeckData] = useState<any>(null);
  const [selectedCopydeckLanguage, setSelectedCopydeckLanguage] = useState<string>("");
  const [isUploadingCopydeck, setIsUploadingCopydeck] = useState(false);
  const copydeckInputRef = useRef<HTMLInputElement>(null);

  // ── LOC Brief State ──────────────────────────────────────────────────
  const [isBriefUploaded, setIsBriefUploaded] = useState(false);
  const [isUploadingBrief, setIsUploadingBrief] = useState(false);
  const briefInputRef = useRef<HTMLInputElement>(null);

  const handleBriefUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setIsUploadingBrief(true);
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      // W środowisku DEV, hardcode jak w Copydeck, w PROD powinno być zmienną środowiskową
      const res = await fetch("http://localhost:8003/api/v1/brief/upload", {
        method: "POST",
        body: formData,
      });
      const json = await res.json();
      if (json.success) {
        setIsBriefUploaded(true);
        // Opcjonalnie mały alert lub toast, my polegamy na zmianie tekstu na przycisku
      } else {
        alert("Błąd wgrywania Briefu: " + json.error);
      }
    } catch (err) {
      console.error(err);
      alert("Błąd połączenia z serwerem podczas wgrywania Briefu.");
    } finally {
      setIsUploadingBrief(false);
      if (briefInputRef.current) briefInputRef.current.value = "";
    }
  };

  const handleCopydeckUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setIsUploadingCopydeck(true);
    const formData = new FormData();
    formData.append("file", file);
    
    try {
      const res = await fetch("http://localhost:8003/api/v1/copydeck/parse", {
        method: "POST",
        body: formData,
      });
      const json = await res.json();
      if (json.success) {
        setCopydeckData(json);
      } else {
        alert("Błąd parsowania Excela: " + json.error);
      }
    } catch (err) {
      console.error(err);
      alert("Błąd połączenia z serwerem.");
    } finally {
      setIsUploadingCopydeck(false);
      if (copydeckInputRef.current) copydeckInputRef.current.value = "";
    }
  };

  const parseFilenameMetadata = (filename: string) => {
    const parts = filename.split('_');
    let country = "Unknown";
    let rating = "Unknown";
    let bing = "PS Logo";
    let bong = "Standard";
    
    if (parts.length > 1) {
      country = parts[1];
      if (country.includes("FR") || country.includes("CA") || country.includes("US")) {
        rating = "ESRB Teen";
      } else {
        rating = "PEGI 18";
      }
      if (country.includes("FR")) {
        bong = "French";
      }
    }
    return { country, rating, bing, bong };
  };

  const runPlaystationQA = async () => {
    if (!acceptanceFile || !acceptanceVideoRef.current) return;
    setIsPsQaAnalyzing(true);
    setPsQaResults(null);
    
    const meta = parseFilenameMetadata(acceptanceFile.name);
    setPsQaMetadata(meta);
    
    try {
      const video = acceptanceVideoRef.current;
      const { w: W, h: H } = getBoundedDimensions(video.videoWidth, video.videoHeight);
      
      const tmpCanvas = document.createElement("canvas");
      tmpCanvas.width = W;
      tmpCanvas.height = H;
      const tmpCtx = tmpCanvas.getContext("2d");
      if (!tmpCtx) {
          setIsPsQaAnalyzing(false);
          return;
      }
      
      const extractFrame = async (time: number): Promise<string> => {
        return new Promise((resolve) => {
          const onSeeked = () => {
            tmpCtx.drawImage(video, 0, 0, W, H);
            const dataUrl = tmpCanvas.toDataURL("image/jpeg", 0.8);
            video.removeEventListener('seeked', onSeeked);
            resolve(dataUrl);
          };
          video.addEventListener('seeked', onSeeked);
          video.currentTime = time;
        });
      };
      
      const originalTime = video.currentTime;
      const wasPlaying = !video.paused;
      if (wasPlaying) video.pause();
      
      const dur = video.duration;
      const frameTimes = [
        0.5, 1.0, 1.5, 2.0, 2.5, 3.0, // BING
        Math.max(0, dur - 1.9), Math.max(0, dur - 1.7), Math.max(0, dur - 1.5), 
        Math.max(0, dur - 1.3), Math.max(0, dur - 1.1), Math.max(0, dur - 0.9), 
        Math.max(0, dur - 0.7), Math.max(0, dur - 0.5) // Covers both BONG shot1 and shot2
      ];
      
      let finalMetaUsed = null;
      
      const analyzeFrame = async (base64: string, timestamp: number) => {
        try {
          const res = await fetch("http://localhost:8003/api/v1/analyze-elements", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image_base64: base64, country_code: meta.country, filename: acceptanceFile.name, timestamp: timestamp })
          });
          return await res.json();
        } catch (e) {
          console.error(e);
          return { rating: false, bing: false, bong: false };
        }
      };

      const tStart = performance.now();
      
      const resultsPromises = [];
      
      for (const t of frameTimes) {
        if (t >= 0 && t <= video.duration) {
          const frame = await extractFrame(t);
          resultsPromises.push(
            analyzeFrame(frame, t).then(res => {
              if (res.metadata_used) {
                finalMetaUsed = res.metadata_used;
              }
              return res;
            })
          );
        }
      }
      
      const results = await Promise.all(resultsPromises);
      
      const tEnd = performance.now();
      const scanTimeMs = tEnd - tStart;
      const scanTimeStr = (scanTimeMs / 1000).toFixed(1) + "s";
      
      // Restore video position
      video.currentTime = originalTime;
      
      let finalRating = "MISSING";
      let finalBing = "MISSING";
      let finalBong = "MISSING";
      let expRating: string | null = null;
      let expBing: string | null = null;
      let expBong: string | null = null;

      for (const res of results) {
         if (res.rating === "FOUND") finalRating = "FOUND";
         else if (res.rating === "INCORRECT" && finalRating !== "FOUND") finalRating = "INCORRECT";

         if (res.bing === "FOUND") finalBing = "FOUND";
         else if (res.bing === "INCORRECT" && finalBing !== "FOUND") finalBing = "INCORRECT";

         if (res.bong === "FOUND") finalBong = "FOUND";
         else if (res.bong === "INCORRECT" && finalBong !== "FOUND") finalBong = "INCORRECT";

         if (res.expected_rating_b64) expRating = res.expected_rating_b64;
         if (res.expected_bing_b64) expBing = res.expected_bing_b64;
         if (res.expected_bong_b64) expBong = res.expected_bong_b64;
      }
      
      setPsQaResults({
        rating: finalRating,
        bing: finalBing,
        bong: finalBong,
        expected_rating_b64: expRating,
        expected_bing_b64: expBing,
        expected_bong_b64: expBong,
        scanTime: scanTimeStr
      });
      
      // Update UI to reflect the actual requirements used by the backend from the LOC Brief
      if (finalMetaUsed && finalMetaUsed.expected_requirements) {
        const reqs = finalMetaUsed.expected_requirements;
        setPsQaMetadata(prev => prev ? {
          ...prev,
          rating: reqs.RATING && reqs.AGE ? `${reqs.RATING} ${reqs.AGE}` : prev.rating,
          bing: reqs.BING || prev.bing,
          bong: reqs.BONG || prev.bong
        } : null);
      }
      
    } catch (err) {
      console.error(err);
    } finally {
      setIsPsQaAnalyzing(false);
    }
  };

  // ── QA Technical Analysis State ─────────────────────────────────────────────
  const [isQaMode, setIsQaMode] = useState(false);
  const [qaDefects, setQaDefects] = useState<{ time: number; type: "black" | "freeze" | "skip" }[]>([]);
  const qaWorkerRef = useRef<Worker | null>(null);
  const qaIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const qaLoggedTimesRef = useRef<Set<number>>(new Set());
  const lastQaFrameDataRef = useRef<ImageData | null>(null);

  // Video Refs
  const acceptanceVideoRef = useRef<HTMLVideoElement>(null);
  const emissionVideoRef = useRef<HTMLVideoElement>(null);

  // Diff overlay refs
  const overlayCanvasRef = useRef<HTMLCanvasElement>(null);
  const diffWorkerRef = useRef<Worker | null>(null);
  const analysisIntervalRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wipeContainerRef = useRef<HTMLDivElement>(null);
  const isDraggingWipeRef = useRef(false);
  // Track already-logged timestamps (keyed by rounded second)
  const loggedTimesRef = useRef<Set<number>>(new Set());
  // Canvas-based wipe display (draws directly from main video refs - no extra <video> elements)
  const wipeCanvasRef = useRef<HTMLCanvasElement>(null);
  // Mirror of wipePosition for use inside RAF closure (avoids stale state)
  const wipePositionRef = useRef(50);
  // requestAnimationFrame handle
  const rafIdRef = useRef<number | null>(null);

  // Check if a file is standard browser playable (like .mp4)
  const isBrowserPlayable = (filename: string) => {
    const ext = filename.split(".").pop()?.toLowerCase();
    return ext === "mp4" || ext === "webm";
  };

  // Helper to format file size
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Clean up object URLs to prevent memory leaks and delete files from server
  const cleanUpFile = (file: VideoFile | null) => {
    if (!file) return;
    
    if (file.isLocal && file.url.startsWith("blob:")) {
      URL.revokeObjectURL(file.url);
    }
    
    // If the file was uploaded to the server (niezależnie czy wygenerowano mp4 czy nie), usuń go trwale
    if (file.fileId !== undefined) {
      // DEV i LIVE różnice w URL, używamy względnego dla proxy w vite
      const apiBase = ''; 
      fetch(`${apiBase}/api/v1/files/${file.fileId}`, {
        method: 'DELETE',
      }).catch(err => console.error("Error deleting file:", err));
    }
  };

  // Handle Drag & Drop Events
  const handleDragEnter = (e: React.DragEvent, type: "acceptance" | "emission") => {
    e.preventDefault();
    e.stopPropagation();
    if (type === "acceptance") setIsDraggingAcceptance(true);
    else setIsDraggingEmission(true);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragLeave = (e: React.DragEvent, type: "acceptance" | "emission") => {
    e.preventDefault();
    e.stopPropagation();
    if (type === "acceptance") setIsDraggingAcceptance(false);
    else setIsDraggingEmission(false);
  };

  // Upload/Process non-native video file (like MXF)
  const uploadAndProcess = async (file: File, type: "acceptance" | "emission") => {
    const isAcc = type === "acceptance";
    let startedPolling = false;

    if (isAcc) {
      // Clear previous poll if any
      if (activePollsRef.current.acceptance) {
        clearTimeout(activePollsRef.current.acceptance);
        activePollsRef.current.acceptance = undefined;
      }
      setAcceptanceLoading(true);
      setAcceptanceError(null);
      setAcceptanceProgress(0);
      setAcceptanceLoadingMessage("Uploading video to server...");
    } else {
      // Clear previous poll if any
      if (activePollsRef.current.emission) {
        clearTimeout(activePollsRef.current.emission);
        activePollsRef.current.emission = undefined;
      }
      setEmissionLoading(true);
      setEmissionError(null);
      setEmissionProgress(0);
      setEmissionLoadingMessage("Uploading video to server...");
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("file_type", type);

    try {
      const response = await fetch("/api/v1/files/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload nie powiódł się, status: ${response.status}`);
      }

      const data = await response.json();
      const fileId = data.file_id;

      // Start asynchronous background transcode polling
      startedPolling = true;
      const startTime = Date.now();

      const pollStatus = async () => {
        try {
          const statusRes = await fetch(`/api/v1/files/${fileId}`);
          if (!statusRes.ok) {
            throw new Error(`Status fetching error: ${statusRes.status}`);
          }
          const fileStatus = await statusRes.json();

          if (fileStatus.is_processed) {
            // Processing success!
            const newFile: VideoFile = {
              url: (() => {
                // Use REACT_APP_API_URL env var (set at startup per environment)
                // LIVE: http://localhost:8001, DEV: http://localhost:8002
                const apiBase = '';
                return `${apiBase}/api/v1/files/stream/${fileId}`;
              })(),
              name: file.name,
              size: file.size,
              isLocal: false,
              fileId: fileId,
              conversionTime: fileStatus.file_metadata?.conversion_time,
            };

            if (isAcc) {
              cleanUpFile(acceptanceFile);
              setAcceptanceFile(newFile);
              setAcceptanceLoading(false);
              setAcceptanceProgress(null);
              setAcceptanceLoadingMessage("");
              if (activePollsRef.current.acceptance) {
                clearTimeout(activePollsRef.current.acceptance);
                activePollsRef.current.acceptance = undefined;
              }
            } else {
              cleanUpFile(emissionFile);
              setEmissionFile(newFile);
              setEmissionLoading(false);
              setEmissionProgress(null);
              setEmissionLoadingMessage("");
              if (activePollsRef.current.emission) {
                clearTimeout(activePollsRef.current.emission);
                activePollsRef.current.emission = undefined;
              }
            }
          } else if (fileStatus.processing_error) {
            // Transcoding failed on FFmpeg side
            throw new Error(fileStatus.processing_error);
          } else {
            // Still processing, update elapsed time and queue next poll
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            const progress = fileStatus.file_metadata?.transcode_progress;
            
            if (isAcc) {
              if (typeof progress === "number") {
                setAcceptanceProgress(progress);
                setAcceptanceLoadingMessage(`Transcoding video... ${progress}% (elapsed ${elapsed}s)`);
              } else {
                setAcceptanceLoadingMessage(`Transcoding video... (elapsed ${elapsed}s)`);
              }
              activePollsRef.current.acceptance = setTimeout(pollStatus, 2000);
            } else {
              if (typeof progress === "number") {
                setEmissionProgress(progress);
                setEmissionLoadingMessage(`Transcoding video... ${progress}% (elapsed ${elapsed}s)`);
              } else {
                setEmissionLoadingMessage(`Transcoding video... (elapsed ${elapsed}s)`);
              }
              activePollsRef.current.emission = setTimeout(pollStatus, 2000);
            }
          }
        } catch (pollErr: any) {
          console.error(`Error during status polling ${type}:`, pollErr);
          const errorMsg = pollErr.message || "Video file transcoding error.";
          if (isAcc) {
            setAcceptanceError(errorMsg);
            setAcceptanceLoading(false);
            setAcceptanceProgress(null);
            setAcceptanceLoadingMessage("");
            if (activePollsRef.current.acceptance) {
              clearTimeout(activePollsRef.current.acceptance);
              activePollsRef.current.acceptance = undefined;
            }
          } else {
            setEmissionError(errorMsg);
            setEmissionLoading(false);
            setEmissionProgress(null);
            setEmissionLoadingMessage("");
            if (activePollsRef.current.emission) {
              clearTimeout(activePollsRef.current.emission);
              activePollsRef.current.emission = undefined;
            }
          }
        }
      };

      // Trigger initial poll after 1s
      if (isAcc) {
        activePollsRef.current.acceptance = setTimeout(pollStatus, 1000);
      } else {
        activePollsRef.current.emission = setTimeout(pollStatus, 1000);
      }

    } catch (err: any) {
      console.error(`Upload error/file processing ${type}:`, err);
      const errorMsg = err.message || "Failed to upload and process video.";
      if (isAcc) {
        setAcceptanceError(errorMsg);
      } else {
        setEmissionError(errorMsg);
      }
    } finally {
      // If we failed before polling started, clear loading state immediately
      if (!startedPolling) {
        if (isAcc) {
          setAcceptanceLoading(false);
          setAcceptanceLoadingMessage("");
        } else {
          setEmissionLoading(false);
          setEmissionLoadingMessage("");
        }
      }
    }
  };

  const handleDrop = (e: React.DragEvent, type: "acceptance" | "emission") => {
    e.preventDefault();
    e.stopPropagation();
    
    if (type === "acceptance") setIsDraggingAcceptance(false);
    else setIsDraggingEmission(false);

    const files = e.dataTransfer.files;
    if (files.length === 0) return;

    const file = files[0];
    const isAcc = type === "acceptance";

    // Handle Local vs Transcode path
    if (isBrowserPlayable(file.name)) {
      const localUrl = URL.createObjectURL(file);
      const newFile: VideoFile = {
        url: localUrl,
        name: file.name,
        size: file.size,
        isLocal: true,
      };

      if (isAcc) {
        cleanUpFile(acceptanceFile);
        setAcceptanceFile(newFile);
        setAcceptanceError(null);
      } else {
        cleanUpFile(emissionFile);
        setEmissionFile(newFile);
        setEmissionError(null);
      }
    } else {
      // MXF or ProRes MOV: Needs backend transcoding
      uploadAndProcess(file, type);
    }
  };

  // Synchronized Playback Handlers
  const togglePlayPause = () => {
    const videos = [acceptanceVideoRef.current, emissionVideoRef.current];
    if (isPlaying) {
      videos.forEach((video) => video?.pause());
    } else {
      // Seek both to current timeline before playing to maintain strict sync
      if (acceptanceVideoRef.current) acceptanceVideoRef.current.currentTime = currentTime + acceptanceTrim;
      if (emissionVideoRef.current) emissionVideoRef.current.currentTime = currentTime + emissionTrim;
      // Attach .catch() DIRECTLY to the play promise to prevent React Error Overlay from intercepting it
      videos.forEach((video) => {
        if (video) {
          const playPromise = video.play();
          if (playPromise !== undefined) {
            playPromise.catch((err: any) => {
              if (err?.name !== 'AbortError') {
                console.error('[Player] play() error:', err);
              }
            });
          }
        }
      });
    }
    setIsPlaying(!isPlaying);
  };

  const handleStop = () => {
    const videos = [acceptanceVideoRef.current, emissionVideoRef.current];
    videos.forEach((video) => {
      if (video) {
        video.pause();
        video.currentTime = 0;
      }
    });
    setIsPlaying(false);
    setCurrentTime(0);
    if (isQaMode) deactivateQaMode();
  };

  const handleRefresh = () => {
    // IMPORTANT: Do NOT call video.load() here — it resets the element to HAVE_NOTHING
    // state and causes onError to fire before the video can rebuffer, crashing both players.
    // Simply seeking to 0 is safe for both blob URLs and server streams.
    const videos = [acceptanceVideoRef.current, emissionVideoRef.current];
    const wasPlaying = isPlaying;

    // Pause both videos first
    videos.forEach((video) => video?.pause());
    setIsPlaying(false);

    // Seek both to start — use canplay event to ensure video is ready before playing
    let readyCount = 0;
    const totalActive = videos.filter(Boolean).length;

    videos.forEach((video) => {
      if (!video) return;

      const onSeeked = () => {
        video.removeEventListener('seeked', onSeeked);
        readyCount++;
        if (wasPlaying && readyCount >= totalActive) {
          // Both seeked — resume playback
          videos.forEach((v) => {
            if (v) {
              const playPromise = v.play();
              if (playPromise !== undefined) {
                playPromise.catch((err: any) => {
                  if (err?.name !== 'AbortError') {
                    console.error('[Player] refresh play() error:', err);
                  }
                });
              }
            }
          });
          setIsPlaying(true);
        }
      };

      video.addEventListener('seeked', onSeeked);
      video.currentTime = 0;
    });

    setCurrentTime(0);
  };

  const handleClear = () => {
    handleStop();
    
    // Clear any active transcode polling timers to prevent leaks
    if (activePollsRef.current.acceptance) {
      clearTimeout(activePollsRef.current.acceptance);
      activePollsRef.current.acceptance = undefined;
    }
    if (activePollsRef.current.emission) {
      clearTimeout(activePollsRef.current.emission);
      activePollsRef.current.emission = undefined;
    }

    cleanUpFile(acceptanceFile);
    cleanUpFile(emissionFile);
    setAcceptanceFile(null);
    setEmissionFile(null);
    setAcceptanceLoading(false);
    setEmissionLoading(false);
    setAcceptanceLoadingMessage("");
    setEmissionLoadingMessage("");
    setAcceptanceProgress(null);
    setEmissionProgress(null);
    setAcceptanceError(null);
    setEmissionError(null);
    setDuration(0);
    setCurrentTime(0);
    setAcceptanceTrim(0);
    setEmissionTrim(0);
    setOcrBoxAcceptance(null);
    setOcrBoxEmission(null);
    setOcrTextAcceptance("");
    setOcrTextEmission("");
    setOcrBriefText("");
  };

  const getMouseSourceCoordinates = (e: React.MouseEvent<HTMLVideoElement>, videoRef: React.RefObject<HTMLVideoElement | null>) => {
    const video = videoRef.current;
    if (!video || video.readyState < 2) return null;

    const rect = video.getBoundingClientRect();
    const videoRatio = video.videoWidth / video.videoHeight;
    const containerRatio = rect.width / rect.height;

    let renderedWidth, renderedHeight, offsetX = 0, offsetY = 0;
    if (containerRatio > videoRatio) {
      renderedHeight = rect.height;
      renderedWidth = rect.height * videoRatio;
      offsetX = (rect.width - renderedWidth) / 2;
    } else {
      renderedWidth = rect.width;
      renderedHeight = rect.width / videoRatio;
      offsetY = (rect.height - renderedHeight) / 2;
    }

    const mouseX = e.clientX - rect.left - offsetX;
    const mouseY = e.clientY - rect.top - offsetY;

    if (mouseX < 0 || mouseX > renderedWidth || mouseY < 0 || mouseY > renderedHeight) {
      return null;
    }

    const sourceX = (mouseX / renderedWidth) * video.videoWidth;
    const sourceY = (mouseY / renderedHeight) * video.videoHeight;

    return { sourceX, sourceY, video, renderedWidth, renderedHeight, offsetX, offsetY, rect };
  };

  const handleVideoMouseDown = (e: React.MouseEvent<HTMLVideoElement>, videoRef: React.RefObject<HTMLVideoElement | null>) => {
    if (isPlaying) return;

    if (isRulerActive) {
      const coords = getMouseSourceCoordinates(e, videoRef);
      if (!coords) return;
      const sourceVideo = videoRef === acceptanceVideoRef ? "acceptance" : "emission";
      
      setActiveRulerLine({
        startX: coords.sourceX,
        startY: coords.sourceY,
        endX: coords.sourceX,
        endY: coords.sourceY,
        sourceVideo,
        color: rulerColor
      });
      return;
    }

    if (isOcrActive) {
      const coords = getMouseSourceCoordinates(e, videoRef);
      if (!coords) return;
      const sourceVideo = videoRef === acceptanceVideoRef ? "acceptance" : "emission";
      
      setActiveOcrBox({
        startX: coords.sourceX,
        startY: coords.sourceY,
        endX: coords.sourceX,
        endY: coords.sourceY,
        sourceVideo
      });
      return;
    }

    if (isEyedropperActive) {
      const coords = getMouseSourceCoordinates(e, videoRef);
      if (!coords) return;
      const { sourceX, sourceY, video } = coords;
      const sourceVideo = videoRef === acceptanceVideoRef ? "acceptance" : "emission";

      const canvas = document.createElement("canvas");
      canvas.width = 1;
      canvas.height = 1;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) return;

      try {
        ctx.drawImage(video, sourceX, sourceY, 1, 1, 0, 0, 1, 1);
        const pixel = ctx.getImageData(0, 0, 1, 1).data;
        const r = pixel[0], g = pixel[1], b = pixel[2];
        const hex = "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();
        
        setEyedropperDrops(prev => [...prev, {
          r, g, b, hex, sourceX, sourceY, sourceVideo
        }]);
      } catch (err) {
        // ignore
      }
    }
  };

  const handleVideoMouseMove = (e: React.MouseEvent<HTMLVideoElement>, videoRef: React.RefObject<HTMLVideoElement | null>) => {
    if (isRulerActive && activeRulerLine && !isPlaying) {
      const coords = getMouseSourceCoordinates(e, videoRef);
      if (coords) {
        setActiveRulerLine({
          ...activeRulerLine,
          endX: coords.sourceX,
          endY: coords.sourceY
        });
      }
    }

    if (isOcrActive && activeOcrBox && !isPlaying) {
      const coords = getMouseSourceCoordinates(e, videoRef);
      if (coords) {
        setActiveOcrBox({
          ...activeOcrBox,
          endX: coords.sourceX,
          endY: coords.sourceY
        });
      }
      return;
    }

    if (!isEyedropperActive || isPlaying) {
      if (hoverColor) setHoverColor(null);
      return;
    }
    
    const coords = getMouseSourceCoordinates(e, videoRef);
    if (!coords) return;
    
    const { sourceX, sourceY, video } = coords;

    const canvas = document.createElement("canvas");
    canvas.width = 1;
    canvas.height = 1;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;

    try {
      ctx.drawImage(video, sourceX, sourceY, 1, 1, 0, 0, 1, 1);
      const pixel = ctx.getImageData(0, 0, 1, 1).data;
      
      const r = pixel[0], g = pixel[1], b = pixel[2];
      const hex = "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).toUpperCase();

      const sourceVideo = videoRef === acceptanceVideoRef ? "acceptance" : "emission";
      setHoverColor({ r, g, b, hex, x: e.clientX, y: e.clientY, sourceX, sourceY, sourceVideo });
    } catch (err) {
      setHoverColor(null);
    }
  };

  const handleVideoMouseUp = () => {
    if (isRulerActive && activeRulerLine) {
      setRulerLines(prev => [...prev, activeRulerLine]);
      setActiveRulerLine(null);
    }
    
    if (isOcrActive && activeOcrBox) {
      const box = {
        startX: Math.min(activeOcrBox.startX, activeOcrBox.endX),
        startY: Math.min(activeOcrBox.startY, activeOcrBox.endY),
        endX: Math.max(activeOcrBox.startX, activeOcrBox.endX),
        endY: Math.max(activeOcrBox.startY, activeOcrBox.endY),
      };
      
      // Ensure box is at least 10x10 to be valid
      if (box.endX - box.startX > 10 && box.endY - box.startY > 10) {
        if (activeOcrBox.sourceVideo === "acceptance") {
          setOcrBoxAcceptance(box);
        } else {
          setOcrBoxEmission(box);
        }
      }
      setActiveOcrBox(null);
    }
  };

  const handleSeek = (time: number) => {
    if (acceptanceVideoRef.current) {
      acceptanceVideoRef.current.currentTime = time + acceptanceTrim;
    }
    if (emissionVideoRef.current) {
      emissionVideoRef.current.currentTime = time + emissionTrim;
    }
    setCurrentTime(time);
  };



  const handleStep = (frames: number) => {
    // Zakładamy 25 fps jako standard dla broadcast
    const fps = 25;
    const stepTime = frames / fps; 
    const newTime = Math.max(0, Math.min(currentTime + stepTime, duration));
    
    const videos = [acceptanceVideoRef.current, emissionVideoRef.current];
    if (isPlaying) {
      videos.forEach((video) => video?.pause());
      setIsPlaying(false);
    }
    
    handleSeek(newTime);
  };

  // ── Keyboard Controls ───────────────────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input or textarea
      const target = e.target as HTMLElement | null;
      if (
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable
      ) {
        return;
      }

      if (e.code === "Space") {
        e.preventDefault(); // Prevent scrolling
        togglePlayPause();
      } else if (e.code === "ArrowRight") {
        e.preventDefault();
        handleStep(1); // One frame forward
      } else if (e.code === "ArrowLeft") {
        e.preventDefault();
        handleStep(-1); // One frame backward
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }); // Run on every render to ensure fresh closures for togglePlayPause and handleStep


  // ── Diff Overlay Logic ───────────────────────────────────────────────────

  /** Teleport both players to a specific timestamp and pause */
  const teleportToTimestamp = useCallback((time: number) => {
    if (acceptanceVideoRef.current) {
      acceptanceVideoRef.current.pause();
      acceptanceVideoRef.current.currentTime = time + acceptanceTrim;
    }
    if (emissionVideoRef.current) {
      emissionVideoRef.current.pause();
      emissionVideoRef.current.currentTime = time + emissionTrim;
    }
    setIsPlaying(false);
    setCurrentTime(time);
  }, []);

  /** Capture one frame from each video, diff them in the Worker, paint overlay */
  const analyzeCurrentFrame = useCallback(() => {
    const accVideo = acceptanceVideoRef.current;
    const emiVideo = emissionVideoRef.current;
    const canvas = overlayCanvasRef.current;
    if (!accVideo || !emiVideo || !canvas || !diffWorkerRef.current) return;
    if (accVideo.readyState < 2 || emiVideo.readyState < 2) return;

    // Use the smaller of the two resolutions to avoid stretching
    const { w: W, h: H } = getBoundedDimensions(accVideo.videoWidth, accVideo.videoHeight);
    if (W === 0 || H === 0) return;

    canvas.width  = W;
    canvas.height = H;

    // Temporary canvas to extract pixel data
    const tmpCanvas = document.createElement("canvas");
    tmpCanvas.width = W;
    tmpCanvas.height = H;
    const tmpCtx = tmpCanvas.getContext("2d", { willReadFrequently: true })!;

    tmpCtx.drawImage(accVideo, 0, 0, W, H);
    const accData = tmpCtx.getImageData(0, 0, W, H);

    tmpCtx.clearRect(0, 0, W, H);
    tmpCtx.drawImage(emiVideo, 0, 0, W, H);
    const emiData = tmpCtx.getImageData(0, 0, W, H);

    diffWorkerRef.current.postMessage(
      { acceptanceData: accData, emissionData: emiData, width: W, height: H },
      [accData.data.buffer, emiData.data.buffer]
    );
  }, []);

  
  // ── QA Technical Analysis Logic ──────────────────────────────────────────
  const analyzeQaFrame = useCallback(() => {
    const video = acceptanceVideoRef.current;
    if (!video || !qaWorkerRef.current) return;
    if (video.readyState < 2) return;

    const { w: W, h: H } = getBoundedDimensions(video.videoWidth, video.videoHeight);
    if (W === 0 || H === 0) return;

    const tmpCanvas = document.createElement("canvas");
    tmpCanvas.width = W;
    tmpCanvas.height = H;
    const tmpCtx = tmpCanvas.getContext("2d", { willReadFrequently: true });
    if (!tmpCtx) return;

    tmpCtx.drawImage(video, 0, 0, W, H);
    const currentData = tmpCtx.getImageData(0, 0, W, H);
    const previousData = lastQaFrameDataRef.current;

    qaWorkerRef.current.postMessage(
      { currentData, previousData, width: W, height: H },
      // We can't transfer currentData buffer because we need it for next frame's previousData
      [] 
    );
    
    lastQaFrameDataRef.current = currentData;
  }, []);

  const activateQaMode = useCallback(() => {
    if (!acceptanceVideoRef.current) return;

    const workerCode = `
      self.onmessage = function(e) {
        var currentData = e.data.currentData;
        var previousData = e.data.previousData;
        var width = e.data.width;
        var height = e.data.height;
        var total = width * height;
        
        var luminanceSum = 0;
        var pixelDiffSum = 0;
        
        for (var i = 0; i < total; i++) {
          var idx = i * 4;
          var r = currentData.data[idx];
          var g = currentData.data[idx+1];
          var b = currentData.data[idx+2];
          
          var lum = 0.299 * r + 0.587 * g + 0.114 * b;
          luminanceSum += lum;
          
          if (previousData) {
            var pr = previousData.data[idx];
            var pg = previousData.data[idx+1];
            var pb = previousData.data[idx+2];
            pixelDiffSum += Math.max(Math.abs(r - pr), Math.abs(g - pg), Math.abs(b - pb));
          }
        }
        
        var avgLuminance = luminanceSum / total;
        var avgDiff = previousData ? (pixelDiffSum / total) : 0;
        
        var isBlack = avgLuminance < 3; // Very dark
        var isFreeze = previousData ? (avgDiff < 1.0) : false; // Extremely low delta
        var isSkip = previousData ? (avgDiff > 60 && avgDiff < 100) : false; // Sudden jump but not full cut
        
        self.postMessage({ avgLuminance, avgDiff, isBlack, isFreeze, isSkip });
      };
    `;
    const blob = new Blob([workerCode], { type: "application/javascript" });
    const worker = new Worker(URL.createObjectURL(blob));
    qaWorkerRef.current = worker;

    worker.onmessage = (e) => {
      const { isBlack, isFreeze, isSkip } = e.data;
      const time = acceptanceVideoRef.current?.currentTime ?? 0;
      const roundedTime = Math.floor(time * 2) / 2; // Granularity of 0.5s

      if (isBlack || isFreeze || isSkip) {
        if (!qaLoggedTimesRef.current.has(roundedTime)) {
          qaLoggedTimesRef.current.add(roundedTime);
          let type: "black" | "freeze" | "skip" = isBlack ? "black" : isFreeze ? "freeze" : "skip";
          setQaDefects(prev => {
            // Avoid adding same type very close to each other
            if (prev.length > 0) {
              const last = prev[prev.length - 1];
              if (last.type === type && Math.abs(last.time - time) < 1.0) return prev;
            }
            return [...prev, { time, type }];
          });
        }
      }
    };

    setIsQaMode(true);
    qaLoggedTimesRef.current.clear();
    setQaDefects([]);
    lastQaFrameDataRef.current = null;

    analyzeQaFrame();
    qaIntervalRef.current = setInterval(() => {
      if (!acceptanceVideoRef.current?.paused) {
        analyzeQaFrame();
      }
    }, 250); // 4 times a second
  }, [analyzeQaFrame]);

  const deactivateQaMode = useCallback(() => {
    if (qaIntervalRef.current) {
      clearInterval(qaIntervalRef.current);
      qaIntervalRef.current = null;
    }
    if (qaWorkerRef.current) {
      qaWorkerRef.current.terminate();
      qaWorkerRef.current = null;
    }
    setIsQaMode(false);
    lastQaFrameDataRef.current = null;
  }, []);

  /** Start diff mode: create Worker, begin periodic analysis */
  const activateDiffMode = useCallback(() => {
    if (!acceptanceVideoRef.current || !emissionVideoRef.current) return;

    // Create off-screen canvas for the diff overlay output.
    // After the wipe-panel refactor the <canvas ref={overlayCanvasRef}> is no longer
    // in the DOM, so we must create it programmatically — otherwise the worker
    // result is discarded and no highlights are shown.
    const offscreen = document.createElement("canvas");
    const { w: offW, h: offH } = getBoundedDimensions(acceptanceVideoRef.current.videoWidth, acceptanceVideoRef.current.videoHeight);
    offscreen.width = offW;
    offscreen.height = offH;
    overlayCanvasRef.current = offscreen;

    // Create Web Worker inline via Blob to avoid CRA webpack Worker loader issues
    const workerCode = `
      const THRESHOLD_AUTOMATION = 30;
      const THRESHOLD_REVIEW = 15;
      self.onmessage = function(e) {
        var acceptanceData = e.data.acceptanceData;
        var emissionData   = e.data.emissionData;
        var width  = e.data.width;
        var height = e.data.height;
        var total  = width * height;
        var overlay = new Uint8ClampedArray(total * 4);
        var certain = 0, review = 0;
        for (var i = 0; i < total; i++) {
          var idx = i * 4;
          var dr = Math.abs(acceptanceData.data[idx]   - emissionData.data[idx]);
          var dg = Math.abs(acceptanceData.data[idx+1] - emissionData.data[idx+1]);
          var db = Math.abs(acceptanceData.data[idx+2] - emissionData.data[idx+2]);
          var m  = Math.max(dr, dg, db);
          if (m > THRESHOLD_AUTOMATION) {
            overlay[idx]=255; overlay[idx+1]=0;   overlay[idx+2]=0;   overlay[idx+3]=230;
            certain++;
          } else if (m > THRESHOLD_REVIEW) {
            overlay[idx]=255; overlay[idx+1]=200; overlay[idx+2]=0;   overlay[idx+3]=200;
            review++;
          } else {
            overlay[idx+3]=0;
          }
        }
        var img = new ImageData(overlay, width, height);
        self.postMessage(
          { overlayData: img, certaintDiffRatio: certain/total, reviewDiffRatio: review/total, hasDifferences: certain>0||review>0 },
          [img.data.buffer]
        );
      };
    `;
    const blob = new Blob([workerCode], { type: "application/javascript" });
    const worker = new Worker(URL.createObjectURL(blob));
    diffWorkerRef.current = worker;

    worker.onmessage = (e: MessageEvent) => {
      const { overlayData, certaintDiffRatio, reviewDiffRatio } = e.data;
      const canvas = overlayCanvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d")!;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (overlayData) ctx.putImageData(overlayData, 0, 0);

      // Log timestamps
      const time = acceptanceVideoRef.current?.currentTime ?? 0;
      const roundedTime = Math.floor(time);
      if (!loggedTimesRef.current.has(roundedTime)) {
        const isCertain = certaintDiffRatio > 0.005;  // >0.5% pixels certain
        const isReview  = reviewDiffRatio   > 0.02;   // >2% pixels review
        if (isCertain || isReview) {
          loggedTimesRef.current.add(roundedTime);
          setDiffTimestamps(prev => [
            ...prev,
            { time, severity: isCertain ? "certain" : "review" }
          ]);
        }
      }
    };

    setDiffMode(true);
    setIsAnalyzing(true);
    loggedTimesRef.current.clear();
    setDiffTimestamps([]);

    // Analyze once immediately, then every 500ms during playback
    analyzeCurrentFrame();
    analysisIntervalRef.current = setInterval(() => {
      if (!acceptanceVideoRef.current?.paused) {
        analyzeCurrentFrame();
      }
    }, 500);
  }, [analyzeCurrentFrame]);

  /** Stop diff mode: terminate Worker, clear overlay */
  const deactivateDiffMode = useCallback(() => {
    if (analysisIntervalRef.current) {
      clearInterval(analysisIntervalRef.current);
      analysisIntervalRef.current = null;
    }
    if (diffWorkerRef.current) {
      diffWorkerRef.current.terminate();
      diffWorkerRef.current = null;
    }
    const canvas = overlayCanvasRef.current;
    if (canvas) {
      const ctx = canvas.getContext("2d");
      ctx?.clearRect(0, 0, canvas.width, canvas.height);
    }
    setDiffMode(false);
    setIsAnalyzing(false);
  }, []);

  /** Clean up worker on unmount */
  useEffect(() => {
    return () => { deactivateDiffMode(); };
  }, [deactivateDiffMode]);

  /** Also run analysis on seek/step when diff mode is active */
  useEffect(() => {
    if (diffMode) {
      analyzeCurrentFrame();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentTime, diffMode]);

  // ── Wipe slider mouse handlers ───────────────────────────────────────────
  const handleWipeMouseDown = (e: React.MouseEvent) => {
    isDraggingWipeRef.current = true;
    e.preventDefault();
  };

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDraggingWipeRef.current || !wipeContainerRef.current) return;
      const rect = wipeContainerRef.current.getBoundingClientRect();
      const pos = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
      setWipePosition(pos);
    };
    const onMouseUp = () => { isDraggingWipeRef.current = false; };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  // Keep wipePositionRef in sync so RAF closure sees the latest value
  useEffect(() => {
    wipePositionRef.current = wipePosition;
  }, [wipePosition]);

  // ── Canvas-based Wipe RAF loop ────────────────────────────────────────────
  // Draws acceptance (clipped) + emission + diff overlay directly from the main
  // video refs. Zero extra <video> elements → no ref hijacking → no freeze.
  useEffect(() => {
    if (!diffMode) {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
      return;
    }

    const drawFrame = () => {
      const accVideo = acceptanceVideoRef.current;
      const emiVideo = emissionVideoRef.current;
      const wipeCanvas = wipeCanvasRef.current;
      const overlayCanvas = overlayCanvasRef.current;

      if (!accVideo || !emiVideo || !wipeCanvas) {
        rafIdRef.current = requestAnimationFrame(drawFrame);
        return;
      }

      // Match canvas resolution to its CSS display size
      const W = wipeCanvas.clientWidth  || 1280;
      const H = wipeCanvas.clientHeight || 720;
      if (wipeCanvas.width !== W)  wipeCanvas.width  = W;
      if (wipeCanvas.height !== H) wipeCanvas.height = H;

      const ctx = wipeCanvas.getContext("2d")!;
      ctx.clearRect(0, 0, W, H);

      const wp = wipePositionRef.current;

      const drawWithLetterbox = (context: CanvasRenderingContext2D, source: HTMLVideoElement | HTMLCanvasElement) => {
        let srcW, srcH;
        if ('videoWidth' in source) {
          srcW = (source as HTMLVideoElement).videoWidth;
          srcH = (source as HTMLVideoElement).videoHeight;
        } else {
          srcW = (source as HTMLCanvasElement).width;
          srcH = (source as HTMLCanvasElement).height;
        }
        
        if (!srcW || !srcH) return;
        
        const videoRatio = srcW / srcH;
        const containerRatio = W / H;
        
        let drawW = W;
        let drawH = H;
        let offsetX = 0;
        let offsetY = 0;
        
        if (containerRatio > videoRatio) {
          // Pillarbox
          drawH = H;
          drawW = H * videoRatio;
          offsetX = (W - drawW) / 2;
        } else {
          // Letterbox
          drawW = W;
          drawH = W / videoRatio;
          offsetY = (H - drawH) / 2;
        }
        
        context.drawImage(source, offsetX, offsetY, drawW, drawH);
      };

      // 1. Draw emission full-width (right side / background)
      if (emiVideo.readyState >= 2) {
        drawWithLetterbox(ctx, emiVideo);
      }

      // 2. Draw acceptance, clipped to the left portion (wipe position)
      if (accVideo.readyState >= 2 && wp > 0) {
        ctx.save();
        ctx.beginPath();
        ctx.rect(0, 0, Math.round(W * wp / 100), H);
        ctx.clip();
        drawWithLetterbox(ctx, accVideo);
        ctx.restore();
      }

      // 3. Diff overlay (source-over — renders at full color, not washed out by screen blend)
      if (overlayCanvas && overlayCanvas.width > 0) {
        ctx.globalAlpha = 0.72;
        ctx.globalCompositeOperation = "source-over";
        drawWithLetterbox(ctx, overlayCanvas);
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "source-over";
      }

      // 4. Wipe divider line + handle
      const lineX = Math.round(W * wp / 100);
      ctx.strokeStyle = "rgba(255,255,255,0.9)";
      ctx.lineWidth = 2;
      ctx.shadowColor = "rgba(255,255,255,0.6)";
      ctx.shadowBlur = 8;
      ctx.beginPath();
      ctx.moveTo(lineX, 0);
      ctx.lineTo(lineX, H);
      ctx.stroke();
      ctx.shadowBlur = 0;

      // Handle circle
      ctx.fillStyle = "#ffffff";
      ctx.beginPath();
      ctx.arc(lineX, H / 2, 16, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "rgba(0,0,0,0.2)";
      ctx.lineWidth = 1;
      ctx.stroke();
      // Arrows inside circle
      ctx.fillStyle = "#374151";
      ctx.font = "bold 12px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("❮❯", lineX, H / 2);
      ctx.textAlign = "left";
      ctx.textBaseline = "alphabetic";

      // 5. Corner labels
      ctx.font = "bold 11px sans-serif";
      ctx.fillStyle = "rgba(34,197,94,0.9)";
      ctx.fillRect(10, 10, 90, 22);
      ctx.fillStyle = "#fff";
      ctx.fillText("ACCEPTANCE", 14, 26);

      ctx.fillStyle = "rgba(239,68,68,0.9)";
      ctx.fillRect(W - 84, 10, 74, 22);
      ctx.fillStyle = "#fff";
      ctx.fillText("EMISSION", W - 80, 26);

      rafIdRef.current = requestAnimationFrame(drawFrame);
    };

    rafIdRef.current = requestAnimationFrame(drawFrame);

    return () => {
      if (rafIdRef.current !== null) {
        cancelAnimationFrame(rafIdRef.current);
        rafIdRef.current = null;
      }
    };
  }, [diffMode]);

  // ── Screenshot ───────────────────────────────────────────────────────────
  const captureScreenshot = useCallback(async () => {
    const accVideo = acceptanceVideoRef.current;
    if (!accVideo) return;
    
    const emiVideo = emissionVideoRef.current;
    if (!isSinglePlayerMode && !emiVideo) return;

    // Pause first so both frames are stable
    const wasPlaying = !accVideo.paused;
    if (wasPlaying) {
      accVideo.pause();
      if (!isSinglePlayerMode && emiVideo) emiVideo.pause();
    }

    // Wait one animation frame so the browser has rendered the paused frame
    await new Promise<void>(resolve => requestAnimationFrame(() => resolve()));

    setScreenshotSaving(true);
    try {
      // Each side: max 960px (total 1920px)
      const SIDE_W = 960;
      const aspectRatio = (accVideo.videoHeight || 720) / (accVideo.videoWidth || 1280);
      const SIDE_H = Math.round(SIDE_W * aspectRatio);
      const LABEL_H = 60;

      const canvas = document.createElement("canvas");
      canvas.width  = isSinglePlayerMode ? SIDE_W : SIDE_W * 2;
      canvas.height = SIDE_H + LABEL_H;
      const ctx = canvas.getContext("2d")!;

      // Dark background
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw frames
      if (accVideo.readyState >= 2) ctx.drawImage(accVideo, 0, LABEL_H, SIDE_W, SIDE_H);
      if (!isSinglePlayerMode && emiVideo && emiVideo.readyState >= 2) {
        ctx.drawImage(emiVideo, SIDE_W, LABEL_H, SIDE_W, SIDE_H);
      }

      // Diff overlay on both sides
      const overlayCanvas = overlayCanvasRef.current;
      if (!isSinglePlayerMode && overlayCanvas && overlayCanvas.width > 0 && diffMode) {
        ctx.globalAlpha = 0.85;
        ctx.globalCompositeOperation = "screen";
        ctx.drawImage(overlayCanvas, 0, LABEL_H, SIDE_W, SIDE_H);
        ctx.drawImage(overlayCanvas, SIDE_W, LABEL_H, SIDE_W, SIDE_H);
        ctx.globalAlpha = 1;
        ctx.globalCompositeOperation = "source-over";
      }

      // Center divider
      if (!isSinglePlayerMode) {
        ctx.strokeStyle = "rgba(255,255,255,0.5)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(SIDE_W, LABEL_H);
        ctx.lineTo(SIDE_W, canvas.height);
        ctx.stroke();
      }

      // Label bar
      const tc = formatTimecode(accVideo.currentTime);
      
      // Green/Purple strip (acceptance)
      ctx.fillStyle = isSinglePlayerMode ? "#4c1d95" : "#14532d";
      ctx.fillRect(0, 0, SIDE_W, LABEL_H);
      ctx.fillStyle = isSinglePlayerMode ? "#c4b5fd" : "#22c55e";
      ctx.font = "bold 18px 'Courier New', monospace";
      ctx.textBaseline = "middle";
      ctx.fillText(isSinglePlayerMode ? "INSPEKCJA" : "ACCEPTANCE", 20, 22);
      ctx.fillStyle = isSinglePlayerMode ? "#e2e8f0" : "#86efac";
      ctx.font = "13px 'Courier New', monospace";
      ctx.fillText(acceptanceFile?.name?.slice(0, 40) ?? "", 20, 46);

      if (!isSinglePlayerMode) {
        // Red strip (emission)
        ctx.fillStyle = "#450a0a";
        ctx.fillRect(SIDE_W, 0, SIDE_W, LABEL_H);
        ctx.fillStyle = "#ef4444";
        ctx.font = "bold 18px 'Courier New', monospace";
        ctx.fillText("EMISSION", SIDE_W + 20, 22);
        ctx.fillStyle = "#fca5a5";
        ctx.font = "13px 'Courier New', monospace";
        ctx.fillText(emissionFile?.name?.slice(0, 40) ?? "", SIDE_W + 20, 46);
      }

      // Timecode centered at top
      ctx.fillStyle = "#1e293b";
      const timecodeX = isSinglePlayerMode ? SIDE_W / 2 : SIDE_W;
      ctx.fillRect(timecodeX - 90, 0, 180, LABEL_H);
      ctx.fillStyle = "#f8fafc";
      ctx.font = "bold 16px 'Courier New', monospace";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(tc, timecodeX, LABEL_H / 2);
      ctx.textAlign = "left";
      ctx.textBaseline = "alphabetic";

      // Diff legend (bottom-right corner)
      if (!isSinglePlayerMode && diffMode) {
        ctx.fillStyle = "rgba(15,23,42,0.85)";
        ctx.fillRect(canvas.width - 210, canvas.height - 56, 200, 50);
        ctx.fillStyle = "#dc2626";
        ctx.fillRect(canvas.width - 198, canvas.height - 44, 14, 14);
        ctx.fillStyle = "#e2e8f0";
        ctx.font = "12px sans-serif";
        ctx.fillText("Pewna różnica", canvas.width - 178, canvas.height - 33);
        ctx.fillStyle = "#eab308";
        ctx.fillRect(canvas.width - 198, canvas.height - 24, 14, 10);
        ctx.fillStyle = "#e2e8f0";
        ctx.fillText("Do sprawdzenia", canvas.width - 178, canvas.height - 14);
      }

      // Eyedropper overlays (pinned drops + current hover)
      const dropsToRender = [...eyedropperDrops];
      if (isEyedropperActive && hoverColor) {
        dropsToRender.push({
          r: hoverColor.r, g: hoverColor.g, b: hoverColor.b, hex: hoverColor.hex,
          sourceX: hoverColor.sourceX, sourceY: hoverColor.sourceY, sourceVideo: hoverColor.sourceVideo
        });
      }

      dropsToRender.forEach((drop) => {
        const isAcc = drop.sourceVideo === "acceptance";
        const scaleX = SIDE_W / (isAcc ? accVideo.videoWidth : (emiVideo?.videoWidth || 1));
        const scaleY = SIDE_H / (isAcc ? accVideo.videoHeight : (emiVideo?.videoHeight || 1));
        
        let drawX = drop.sourceX * scaleX;
        let drawY = drop.sourceY * scaleY + LABEL_H;
        if (!isAcc) drawX += SIDE_W;

        // Offset the box slightly from the exact pixel
        drawX += 20;
        drawY += 20;

        // Keep it inside the canvas
        if (drawX + 160 > canvas.width) drawX -= 180;
        if (drawY + 60 > canvas.height) drawY -= 80;

        // Tooltip Background
        ctx.fillStyle = "rgba(15,23,42,0.95)";
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(drawX, drawY, 150, 44, 8);
        } else {
          ctx.fillRect(drawX, drawY, 150, 44);
        }
        ctx.fill();
        ctx.strokeStyle = "rgba(71,85,105,0.5)";
        ctx.stroke();

        // Color Swatch
        ctx.fillStyle = drop.hex;
        ctx.beginPath();
        if (ctx.roundRect) {
          ctx.roundRect(drawX + 8, drawY + 8, 28, 28, 4);
        } else {
          ctx.fillRect(drawX + 8, drawY + 8, 28, 28);
        }
        ctx.fill();
        ctx.strokeStyle = "rgba(255,255,255,0.2)";
        ctx.stroke();
        
        // Text
        ctx.fillStyle = "#f8fafc";
        ctx.font = "bold 13px 'Courier New', monospace";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(drop.hex, drawX + 44, drawY + 16);
        ctx.fillStyle = "#94a3b8";
        ctx.font = "10px 'Courier New', monospace";
        ctx.fillText(`RGB: ${drop.r}, ${drop.g}, ${drop.b}`, drawX + 44, drawY + 32);
      });

      // Ruler overlay
      if (isRulerActive) {
        const linesToRender = [...rulerLines];
        if (activeRulerLine) linesToRender.push(activeRulerLine);
        
        linesToRender.forEach((line) => {
          const isAcc = line.sourceVideo === "acceptance";
          const scaleX = SIDE_W / (isAcc ? accVideo.videoWidth : (emiVideo?.videoWidth || 1));
          const scaleY = SIDE_H / (isAcc ? accVideo.videoHeight : (emiVideo?.videoHeight || 1));
          
          let drawStartX = line.startX * scaleX;
          let drawStartY = line.startY * scaleY + LABEL_H;
          let drawEndX = line.endX * scaleX;
          let drawEndY = line.endY * scaleY + LABEL_H;
          
          if (!isAcc) {
            drawStartX += SIDE_W;
            drawEndX += SIDE_W;
          }
          
          const dist = Math.round(Math.sqrt(Math.pow(line.endX - line.startX, 2) + Math.pow(line.endY - line.startY, 2)));
          const midX = (drawStartX + drawEndX) / 2;
          const midY = (drawStartY + drawEndY) / 2;
          
          ctx.beginPath();
          ctx.moveTo(drawStartX, drawStartY);
          ctx.lineTo(drawEndX, drawEndY);
          ctx.strokeStyle = line.color;
          ctx.lineWidth = 2;
          ctx.setLineDash([4, 2]);
          ctx.stroke();
          ctx.setLineDash([]);
          
          const angle = Math.atan2(drawEndY - drawStartY, drawEndX - drawStartX);
          const arrowLength = 8;
          const arrowAngle = Math.PI / 6;

          ctx.fillStyle = line.color;
          
          // Draw start arrow
          ctx.beginPath();
          ctx.moveTo(drawStartX, drawStartY);
          ctx.lineTo(drawStartX + arrowLength * Math.cos(angle - arrowAngle), drawStartY + arrowLength * Math.sin(angle - arrowAngle));
          ctx.lineTo(drawStartX + arrowLength * Math.cos(angle + arrowAngle), drawStartY + arrowLength * Math.sin(angle + arrowAngle));
          ctx.closePath();
          ctx.fill();

          // Draw end arrow
          ctx.beginPath();
          ctx.moveTo(drawEndX, drawEndY);
          ctx.lineTo(drawEndX - arrowLength * Math.cos(angle - arrowAngle), drawEndY - arrowLength * Math.sin(angle - arrowAngle));
          ctx.lineTo(drawEndX - arrowLength * Math.cos(angle + arrowAngle), drawEndY - arrowLength * Math.sin(angle + arrowAngle));
          ctx.closePath();
          ctx.fill();
          
          if (dist > 0) {
            ctx.fillStyle = line.color;
            ctx.font = "bold 14px sans-serif";
            ctx.textAlign = "center";
            ctx.strokeStyle = "black";
            ctx.lineWidth = 3;
            ctx.strokeText(`${dist} px`, midX, midY - 8);
            ctx.fillText(`${dist} px`, midX, midY - 8);
          }
        });
      }

      canvas.toBlob((blob) => {
        if (!blob) return;
        const prefix = (acceptanceFile?.name ?? "screenshot")
          .replace(/\.[^.]+$/, "")
          .slice(0, 15)
          .replace(/[^a-zA-Z0-9_-]/g, "_");
        const tcSafe = tc.replace(/:/g, "-");
        const filename = `${prefix}_${tcSafe}.png`;
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
        setScreenshotSaving(false);
        setEyedropperDrops([]);
        // Resume playback if it was playing before
        if (wasPlaying) {
          accVideo.play().catch(() => {});
          emiVideo?.play().catch(() => {});
          setIsPlaying(true);
        }
      }, "image/png");
    } catch (err) {
      console.error("Screenshot failed:", err);
      setScreenshotSaving(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [acceptanceFile, emissionFile, diffMode, isEyedropperActive, hoverColor, isRulerActive, rulerLines, activeRulerLine]);

  // Sync individual volumes & master mute state
  useEffect(() => {
    if (acceptanceVideoRef.current) {
      acceptanceVideoRef.current.volume = isMuted ? 0 : acceptanceVolume;
    }
  }, [acceptanceVolume, isMuted]);

  useEffect(() => {
    if (emissionVideoRef.current) {
      emissionVideoRef.current.volume = isMuted ? 0 : emissionVolume;
    }
  }, [emissionVolume, isMuted]);

  // Sync playhead, duration, and track status
  useEffect(() => {
    const videos = [acceptanceVideoRef.current, emissionVideoRef.current];

    const handleLoadedMetadata = () => {
      // Set duration based on the longest loaded video minus trim
      const accDur = acceptanceVideoRef.current ? Math.max(0, acceptanceVideoRef.current.duration - acceptanceTrim) : 0;
      const emiDur = emissionVideoRef.current ? Math.max(0, emissionVideoRef.current.duration - emissionTrim) : 0;
      setDuration(Math.max(accDur, emiDur));
    };

    const handleTimeUpdate = () => {
      // Use acceptance video as the sync master by default
      if (acceptanceVideoRef.current) {
        const timelineTime = Math.max(0, acceptanceVideoRef.current.currentTime - acceptanceTrim);
        setCurrentTime(timelineTime);

        // Keep the second video in lock-step (threshold of 0.15 seconds)
        if (emissionVideoRef.current && isPlaying) {
          const expectedEmissionTime = timelineTime + emissionTrim;
          if (Math.abs(emissionVideoRef.current.currentTime - expectedEmissionTime) > 0.15) {
            emissionVideoRef.current.currentTime = expectedEmissionTime;
          }
        }
      } else if (emissionVideoRef.current) {
        // Fallback to emission video if acceptance is not loaded
        setCurrentTime(Math.max(0, emissionVideoRef.current.currentTime - emissionTrim));
      }
    };

    const handleEnded = () => {
      // Check if both loaded videos are completed
      const accEnded = acceptanceVideoRef.current ? acceptanceVideoRef.current.ended : true;
      const emiEnded = emissionVideoRef.current ? emissionVideoRef.current.ended : true;
      if (accEnded && emiEnded) {
        setIsPlaying(false);
      }
    };

    videos.forEach((video) => {
      if (video) {
        video.addEventListener("loadedmetadata", handleLoadedMetadata);
        video.addEventListener("timeupdate", handleTimeUpdate);
        video.addEventListener("ended", handleEnded);
      }
    });

    return () => {
      videos.forEach((video) => {
        if (video) {
          video.removeEventListener("loadedmetadata", handleLoadedMetadata);
          video.removeEventListener("timeupdate", handleTimeUpdate);
          video.removeEventListener("ended", handleEnded);
        }
      });
    };
  }, [acceptanceFile, emissionFile, isPlaying, acceptanceTrim, emissionTrim]);

  // Clean up Object URLs and active polling timeouts when component unmounts
  useEffect(() => {
    const currentPolls = activePollsRef.current;
    return () => {
      // Note: We DO NOT call cleanUpFile() here because React StrictMode 
      // unmounts and remounts immediately, which would prematurely revoke 
      // the Blob URLs while they are still in state.
      // Old files are already properly cleaned up in handleDrop/uploadAndProcess.
      
      // Clear all active background timeouts
      if (currentPolls.acceptance) {
        clearTimeout(currentPolls.acceptance);
      }
      if (currentPolls.emission) {
        clearTimeout(currentPolls.emission);
      }
      setAcceptanceProgress(null);
      setEmissionProgress(null);
    };
  }, [acceptanceFile, emissionFile]);

  // Format MM:SS for timeline
  // Format MM:SS for timeline
  const formatTime = (time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, "0")}`;
  };

  // Format MM:SS:FF for timecode (25 fps)
  const formatTimecode = (time: number, fps = 25) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    const frames = Math.floor((time % 1) * fps);
    return `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}:${frames.toString().padStart(2, "0")}`;
  };

  // OCR Lifecycle & Execution
  useEffect(() => {
    if (!isOcrActive) {
      setOcrBoxAcceptance(null);
      setOcrBoxEmission(null);
      setOcrTextAcceptance("");
      setOcrTextEmission("");
      setOcrBriefText("");
      setActiveOcrBox(null);
    }
  }, [isOcrActive]);

  const generateOcrImage = useCallback((video: HTMLVideoElement, box: {startX: number, startY: number, endX: number, endY: number}): string | null => {
    const width = box.endX - box.startX;
    const height = box.endY - box.startY;
    if (width <= 0 || height <= 0) return null;
    
    // Upscale by 3x to improve OCR accuracy for small or compressed video text
    const scale = 3;
    // Add 20px padding to help Tesseract detect text block boundaries
    const padding = 20;
    const canvas = document.createElement("canvas");
    canvas.width = width * scale + padding * 2;
    canvas.height = height * scale + padding * 2;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    
    // Fill background (white by default, black if inverted)
    ctx.fillStyle = ocrInvertColors ? "black" : "white";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Wyłączone wygładzanie (najbliższy sąsiad) zachowuje maksymalny kontrast małych kropek 
    // i linii przy skalowaniu, co o ironio daje Tesseractowi lepsze szanse na przeczytanie Ä/Ö.
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(video, box.startX, box.startY, width, height, padding, padding, width * scale, height * scale);
    
    // Apply grayscale filter, dynamic contrast boost, and optional color inversion
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const data = imageData.data;
    for (let i = 0; i < data.length; i += 4) {
      let avg = (data[i] + data[i + 1] + data[i + 2]) / 3;
      
      // Dynamic contrast boost based on slider
      avg = avg < 128 ? Math.max(0, avg - ocrContrast) : Math.min(255, avg + ocrContrast);
      
      if (ocrInvertColors) {
        avg = 255 - avg;
      }
      
      data[i] = avg;
      data[i + 1] = avg;
      data[i + 2] = avg;
    }
    ctx.putImageData(imageData, 0, 0);

    return canvas.toDataURL("image/png");
  }, [ocrContrast, ocrInvertColors]);

  // Live preview effect
  useEffect(() => {
    if (isOcrActive && ocrBoxAcceptance && acceptanceVideoRef.current && acceptanceVideoRef.current.readyState >= 2) {
      setOcrPreviewAcceptance(generateOcrImage(acceptanceVideoRef.current, ocrBoxAcceptance));
    } else {
      setOcrPreviewAcceptance(null);
    }
    
    if (isOcrActive && ocrBoxEmission && emissionVideoRef.current && emissionVideoRef.current.readyState >= 2) {
      setOcrPreviewEmission(generateOcrImage(emissionVideoRef.current, ocrBoxEmission));
    } else {
      setOcrPreviewEmission(null);
    }
  }, [isOcrActive, ocrBoxAcceptance, ocrBoxEmission, ocrContrast, ocrInvertColors, currentTime, generateOcrImage]);

  // Report Capture Logic
  const handleCaptureReport = async () => {
    if (capturingReport) return;
    setCapturingReport(true);
    
    let acceptanceImage = "";
    let emissionImage = "";
    let diffImage = "";
    let ocrPanelImage = "";
    
    try {
      const captureContainer = async (containerId: string, videoRef: React.RefObject<HTMLVideoElement | null>) => {
        const container = document.getElementById(containerId);
        const videoElement = videoRef.current;
        if (!container || !videoElement) return "";
        
        const fallbackCanvas = document.createElement("canvas");
        fallbackCanvas.width = videoElement.videoWidth;
        fallbackCanvas.height = videoElement.videoHeight;
        const fCtx = fallbackCanvas.getContext("2d");
        if (fCtx) {
          fCtx.drawImage(videoElement, 0, 0, fallbackCanvas.width, fallbackCanvas.height);
          
          const sourceVideo = containerId.includes("acceptance") ? "acceptance" : "emission";
          const baseScale = Math.max(1, fallbackCanvas.height / 800);
          fCtx.lineWidth = 3 * baseScale;
          
          // Draw Rulers
          if (isRulerActive) {
            fCtx.strokeStyle = rulerColor;
            fCtx.fillStyle = rulerColor;
            fCtx.font = `bold ${24 * baseScale}px sans-serif`;
            const linesToRender = [...rulerLines];
            if (activeRulerLine) linesToRender.push(activeRulerLine);
            linesToRender.filter(l => l.sourceVideo === sourceVideo).forEach(line => {
              fCtx.beginPath();
              fCtx.moveTo(line.startX, line.startY);
              fCtx.lineTo(line.endX, line.endY);
              fCtx.stroke();
              
              fCtx.beginPath();
              fCtx.arc(line.startX, line.startY, 5 * baseScale, 0, 2*Math.PI);
              fCtx.fill();
              fCtx.beginPath();
              fCtx.arc(line.endX, line.endY, 5 * baseScale, 0, 2*Math.PI);
              fCtx.fill();
              
              const dist = Math.round(Math.sqrt(Math.pow(line.endX - line.startX, 2) + Math.pow(line.endY - line.startY, 2)));
              fCtx.fillText(`${dist}px`, line.endX + 10 * baseScale, line.endY + 10 * baseScale);
            });
          }
          
          // Draw Eyedroppers
          if (isEyedropperActive) {
            const dropsToRender = [...eyedropperDrops];
            if (hoverColor) dropsToRender.push(hoverColor);
            dropsToRender.filter(d => d.sourceVideo === sourceVideo).forEach(drop => {
              fCtx.strokeStyle = "white";
              fCtx.lineWidth = 2 * baseScale;
              fCtx.beginPath();
              fCtx.arc(drop.sourceX, drop.sourceY, 8 * baseScale, 0, 2 * Math.PI);
              fCtx.stroke();
              
              fCtx.fillStyle = "rgba(0, 0, 0, 0.7)";
              fCtx.fillRect(drop.sourceX + 15 * baseScale, drop.sourceY - 35 * baseScale, 100 * baseScale, 30 * baseScale);
              fCtx.fillStyle = drop.hex;
              fCtx.font = `bold ${16 * baseScale}px monospace`;
              fCtx.fillText(drop.hex, drop.sourceX + 22 * baseScale, drop.sourceY - 14 * baseScale);
            });
          }
        }
        
        try {
          const h2cCanvas = await html2canvas(container, {
            backgroundColor: null,
            useCORS: true,
            scale: 1.5,
            ignoreElements: (node) => node.tagName === "VIDEO"
          });
          
          const finalCanvas = document.createElement("canvas");
          finalCanvas.width = h2cCanvas.width;
          finalCanvas.height = h2cCanvas.height;
          const ctx = finalCanvas.getContext("2d");
          if (ctx) {
            ctx.fillStyle = "#f9fafb";
            ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);
            
            const vRect = videoElement.getBoundingClientRect();
            const cRect = container.getBoundingClientRect();
            
            const scale = 1.5;
            const vLeft = (vRect.left - cRect.left) * scale;
            const vTop = (vRect.top - cRect.top) * scale;
            const vWidth = vRect.width * scale;
            const vHeight = vRect.height * scale;
            
            ctx.drawImage(fallbackCanvas, vLeft, vTop, vWidth, vHeight);
            ctx.drawImage(h2cCanvas, 0, 0);
          }
          return finalCanvas.toDataURL("image/jpeg", 0.8);
        } catch (e) {
          console.warn("html2canvas error, using fallback", e);
          return fallbackCanvas.toDataURL("image/jpeg", 0.8);
        }
      };

      acceptanceImage = await captureContainer("acceptance-container", acceptanceVideoRef);
      if (!isSinglePlayerMode) {
        emissionImage = await captureContainer("emission-container", emissionVideoRef);
      }
      
      if (!isSinglePlayerMode && diffMode && wipeCanvasRef.current) {
        try { diffImage = wipeCanvasRef.current.toDataURL("image/jpeg", 0.8); } catch(e) {}
      }
      if (isOcrActive) {
        const ocrPanel = document.getElementById("ocr-panel-container");
        if (ocrPanel) {
          try {
            const ocrCanvas = await html2canvas(ocrPanel, { backgroundColor: "#f9fafb", useCORS: true, scale: 1.5 });
            ocrPanelImage = ocrCanvas.toDataURL("image/jpeg", 0.8);
          } catch (e) {
            console.warn("Failed to capture OCR panel:", e);
          }
        }
      }
    } catch (err) {
      console.error("Failed to capture report screenshots:", err);
    }

    setPendingReportItem({
        id: Date.now().toString(),
        timecode: currentTime,
        type: isSinglePlayerMode ? "single" : "unified",
        comment: "",
        acceptanceImage,
        emissionImage,
        diffImage,
        ocrPanelImage,
        ocrTextAcceptance: isOcrActive ? ocrTextAcceptance : undefined,
        ocrTextEmission: (isOcrActive && !isSinglePlayerMode) ? ocrTextEmission : undefined,
        ocrBriefText: isOcrActive ? ocrBriefText : undefined,
      });
    setCapturingReport(false);
  };

  const removeAccents = (str: string) => {
    if (!str) return "";
    return str
      .replace(/ą/g, 'a').replace(/Ą/g, 'A')
      .replace(/ć/g, 'c').replace(/Ć/g, 'C')
      .replace(/ę/g, 'e').replace(/Ę/g, 'E')
      .replace(/ł/g, 'l').replace(/Ł/g, 'L')
      .replace(/ń/g, 'n').replace(/Ń/g, 'N')
      .replace(/ó/g, 'o').replace(/Ó/g, 'O')
      .replace(/ś/g, 's').replace(/Ś/g, 'S')
      .replace(/ź/g, 'z').replace(/Ź/g, 'Z')
      .replace(/ż/g, 'z').replace(/Ż/g, 'Z')
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  };

  const generatePDF = () => {
    const doc = new jsPDF();
    doc.setFont("helvetica", "bold");
    doc.setFontSize(20);
    doc.text("QA Report - Sync DualPlayer", 20, 20);
    
    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.text(`Data wygenerowania: ${new Date().toLocaleString()}`, 20, 30);
    if (acceptanceFile) doc.text(`Acceptance: ${acceptanceFile.name}`, 20, 38);
    if (emissionFile) doc.text(`Emission: ${emissionFile.name}`, 20, 44);

    let yOffset = 55;
    
    reportItems.forEach((item, index) => {
      // Add new page if we are near the bottom
      if (yOffset > 220) {
        doc.addPage();
        yOffset = 20;
      }
      
      // Header for item
      doc.setFillColor(243, 244, 246);
      doc.rect(20, yOffset - 5, 170, 8, "F");
      doc.setFont("helvetica", "bold");
      doc.setFontSize(12);
      doc.setTextColor(31, 41, 55);
      doc.text(`Zrzut #${index + 1} - Video time: ${item.timecode.toFixed(3)}s [Typ: ${item.type.toUpperCase()}]`, 22, yOffset);
      yOffset += 10;
      
      // Comment
      doc.setFont("helvetica", "normal");
      doc.setFontSize(10);
      if (item.comment) {
        doc.setFont("helvetica", "italic");
        const lines = doc.splitTextToSize(`Komentarz: ${removeAccents(item.comment)}`, 160);
        doc.text(lines, 20, yOffset);
        yOffset += (lines.length * 5) + 5;
        doc.setFont("helvetica", "normal");
      }

      if (item.type === "visual" || item.type === "unified" || item.type === "single") {
        let hasVideoImages = false;
        if (item.type === "single" && item.acceptanceImage) {
          hasVideoImages = true;
          doc.setFontSize(9);
          doc.text("Video (Inspekcja):", 20, yOffset);
          doc.addImage(item.acceptanceImage, "JPEG", 20, yOffset + 3, 170, 95);
          yOffset += 105;
        } else {
          if (item.acceptanceImage) {
            hasVideoImages = true;
            doc.setFontSize(9);
            doc.text("Video Acceptance:", 20, yOffset);
            doc.addImage(item.acceptanceImage, "JPEG", 20, yOffset + 3, 80, 45);
          }
          if (item.emissionImage) {
            hasVideoImages = true;
            doc.setFontSize(9);
            doc.text("Video Emission:", 110, yOffset);
            doc.addImage(item.emissionImage, "JPEG", 110, yOffset + 3, 80, 45);
          }
          if (hasVideoImages) yOffset += 55;
        }

        if (item.diffImage) {
          if (yOffset > 220) { doc.addPage(); yOffset = 20; }
          doc.setFontSize(9);
          doc.text("Wipe / Diff View (Overlay):", 20, yOffset);
          doc.addImage(item.diffImage, "JPEG", 20, yOffset + 3, 170, 95);
          yOffset += 105;
        }

        if (item.ocrPanelImage) {
          if (yOffset > 180) { doc.addPage(); yOffset = 20; }
          doc.setFontSize(9);
          doc.text("Wyniki i Roznice OCR (Zrzut Panelu):", 20, yOffset);
          doc.addImage(item.ocrPanelImage, "JPEG", 20, yOffset + 3, 170, 100);
          yOffset += 110;
        }

        if (item.ocrTextAcceptance || item.ocrTextEmission) {
          if (yOffset > 240) { doc.addPage(); yOffset = 20; }
          
          doc.setFontSize(10);
          doc.setFont("helvetica", "bold");
          doc.text("Odczyt OCR i Roznice Tekstu:", 20, yOffset);
          yOffset += 6;
          
          const accBase = item.ocrTextAcceptance || "None odczytu.";
          const emBase = item.ocrTextEmission || "None odczytu.";
          const briefBase = item.ocrBriefText || accBase;

          const renderColoredDiff = (text1: string, text2: string, startX: number, startY: number, maxWidth: number) => {
            const parts = diffWords(text1, text2);
            let currentX = startX;
            let currentY = startY;
            doc.setFontSize(9);
            
            parts.forEach(part => {
              if (part.added) { doc.setTextColor(22, 163, 74); doc.setFont("helvetica", "bold"); }
              else if (part.removed) { doc.setTextColor(220, 38, 38); doc.setFont("helvetica", "bold"); }
              else { doc.setTextColor(55, 65, 81); doc.setFont("helvetica", "normal"); }
              
              const words = part.value.split(/(\s+)/);
              words.forEach(word => {
                if (!word) return;
                if (word === '\n') {
                  currentY += 5;
                  currentX = startX;
                  return;
                }
                const cleanWord = removeAccents(word);
                const w = doc.getTextWidth(cleanWord);
                if (currentX + w > startX + maxWidth) {
                  currentY += 5;
                  currentX = startX;
                  if (word.trim() === '') return;
                }
                doc.text(cleanWord, currentX, currentY);
                currentX += w;
              });
            });
            doc.setTextColor(31, 41, 55);
            doc.setFont("helvetica", "normal");
            return currentY + 7;
          };

          if (item.type === "single") {
            doc.setFontSize(9);
            doc.setFont("helvetica", "normal");
            doc.text("Video:", 20, yOffset);
            yOffset += 4;
            yOffset = renderColoredDiff(briefBase, accBase, 20, yOffset, 160);
          } else {
            doc.setFontSize(9);
            doc.setFont("helvetica", "normal");
            doc.text("Acceptance:", 20, yOffset);
            yOffset += 4;
            yOffset = renderColoredDiff(briefBase, accBase, 20, yOffset, 160);
            
            doc.setFont("helvetica", "normal");
            doc.setTextColor(31, 41, 55);
            doc.text("Emission:", 20, yOffset);
            yOffset += 4;
            yOffset = renderColoredDiff(briefBase, emBase, 20, yOffset, 160);
            
            if (item.ocrBriefText && item.ocrTextAcceptance && item.ocrTextEmission) {
              doc.setFont("helvetica", "bold");
              doc.setTextColor(31, 41, 55);
              doc.text("Direct comparison (Acc vs Em):", 20, yOffset);
              yOffset += 4;
              yOffset = renderColoredDiff(accBase, emBase, 20, yOffset, 160);
            }
          }
        }
      }
      
      yOffset += 5;
    });

    doc.save("Raport_QA.pdf");
  };

  const handleRunOcr = async () => {
    setIsOcrProcessing(true);
    setOcrProgressMessage("");
    try {
      const activeLang = ocrLanguage === "custom" && ocrCustomLanguage.length > 0 ? ocrCustomLanguage : (ocrLanguage === "custom" ? "eng" : ocrLanguage);

      if (ocrBoxAcceptance && ocrPreviewAcceptance) {
        const result = await Tesseract.recognize(ocrPreviewAcceptance, activeLang, {
          logger: m => {
            if (m.status === "loading tesseract core") setOcrProgressMessage("Ładowanie silnika OCR...");
            else if (m.status === "loading language traineddata") setOcrProgressMessage(`Pobieranie paczki języka: ${(m.progress * 100).toFixed(0)}%`);
            else if (m.status === "initializing api") setOcrProgressMessage("Inicjalizacja API...");
            else if (m.status === "recognizing text") setOcrProgressMessage(`Czytanie tekstu: ${(m.progress * 100).toFixed(0)}%`);
          }
        });
        setOcrTextAcceptance(result.data.text.trim());
      }
      
      if (!isSinglePlayerMode && ocrBoxEmission && ocrPreviewEmission) {
        const result = await Tesseract.recognize(ocrPreviewEmission, activeLang);
        setOcrTextEmission(result.data.text.trim());
      }
    } catch (error) {
      console.error("Critical OCR error:", error);
      alert("Wystąpił błąd podczas analizy obrazu. Spróbuj powtórzyć operację lub zmienić parametry.");
    } finally {
      setIsOcrProcessing(false);
      setOcrProgressMessage("");
    }
  };

  const renderRulerOverlay = (sourceVideo: "acceptance" | "emission", containerRef: React.RefObject<HTMLVideoElement | null>) => {
    if (!isRulerActive) return null;
    
    const video = containerRef.current;
    if (!video || video.readyState < 2) return null;
    
    const rect = video.getBoundingClientRect();
    const videoRatio = video.videoWidth / video.videoHeight;
    const containerRatio = rect.width / rect.height;

    let renderedWidth: number, renderedHeight: number, offsetX = 0, offsetY = 0;
    if (containerRatio > videoRatio) {
      renderedHeight = rect.height;
      renderedWidth = rect.height * videoRatio;
      offsetX = (rect.width - renderedWidth) / 2;
    } else {
      renderedWidth = rect.width;
      renderedHeight = rect.width / videoRatio;
      offsetY = (rect.height - renderedHeight) / 2;
    }

    const mapToScreen = (sx: number, sy: number) => ({
      x: (sx / video.videoWidth) * renderedWidth + offsetX,
      y: (sy / video.videoHeight) * renderedHeight + offsetY
    });

    const calculateDistance = (line: RulerLine) => {
      return Math.round(Math.sqrt(Math.pow(line.endX - line.startX, 2) + Math.pow(line.endY - line.startY, 2)));
    };

    const linesToRender = [...rulerLines];
    if (activeRulerLine) linesToRender.push(activeRulerLine);

    return (
      <svg xmlns="http://www.w3.org/2000/svg" className="absolute top-4 left-4 w-[calc(100%-2rem)] h-[calc(100%-2rem)] pointer-events-none z-20">
        {linesToRender.filter(l => l.sourceVideo === sourceVideo).map((line, i) => {
          const start = mapToScreen(line.startX, line.startY);
          const end = mapToScreen(line.endX, line.endY);
          const dist = calculateDistance(line);
          const midX = (start.x + end.x) / 2;
          const midY = (start.y + end.y) / 2;
          
          const angle = Math.atan2(end.y - start.y, end.x - start.x);
          const arrowLength = 8;
          const arrowAngle = Math.PI / 6;

          const p1 = {
            x: start.x + arrowLength * Math.cos(angle - arrowAngle),
            y: start.y + arrowLength * Math.sin(angle - arrowAngle)
          };
          const p2 = {
            x: start.x + arrowLength * Math.cos(angle + arrowAngle),
            y: start.y + arrowLength * Math.sin(angle + arrowAngle)
          };
          const p3 = {
            x: end.x - arrowLength * Math.cos(angle - arrowAngle),
            y: end.y - arrowLength * Math.sin(angle - arrowAngle)
          };
          const p4 = {
            x: end.x - arrowLength * Math.cos(angle + arrowAngle),
            y: end.y - arrowLength * Math.sin(angle + arrowAngle)
          };

          return (
            <g key={i}>
              <line x1={start.x} y1={start.y} x2={end.x} y2={end.y} stroke={line.color} strokeWidth="2" strokeDasharray="4 2" />
              <polygon points={`${start.x},${start.y} ${p1.x},${p1.y} ${p2.x},${p2.y}`} fill={line.color} />
              <polygon points={`${end.x},${end.y} ${p3.x},${p3.y} ${p4.x},${p4.y}`} fill={line.color} />
              {dist > 0 && (
                <text x={midX} y={midY - 8} fill={line.color} fontSize="12" fontWeight="bold" textAnchor="middle" style={{ textShadow: "0px 1px 3px rgba(0,0,0,0.8), 0px 0px 2px rgba(0,0,0,1)" }}>
                  {dist} px
                </text>
              )}
            </g>
          );
        })}
      </svg>
    );
  };

  const renderEyedropperOverlay = (sourceVideo: "acceptance" | "emission", containerRef: React.RefObject<HTMLVideoElement | null>) => {
    if (!isEyedropperActive) return null;
    
    const video = containerRef.current;
    if (!video || video.readyState < 2) return null;
    
    const rect = video.getBoundingClientRect();
    const videoRatio = video.videoWidth / video.videoHeight;
    const containerRatio = rect.width / rect.height;

    let renderedWidth: number, renderedHeight: number, offsetX = 0, offsetY = 0;
    if (containerRatio > videoRatio) {
      renderedHeight = rect.height;
      renderedWidth = rect.height * videoRatio;
      offsetX = (rect.width - renderedWidth) / 2;
    } else {
      renderedWidth = rect.width;
      renderedHeight = rect.width / videoRatio;
      offsetY = (rect.height - renderedHeight) / 2;
    }

    const mapToScreen = (sx: number, sy: number) => ({
      x: (sx / video.videoWidth) * renderedWidth + offsetX,
      y: (sy / video.videoHeight) * renderedHeight + offsetY
    });

    return (
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none z-20 overflow-hidden">
        {eyedropperDrops.filter(d => d.sourceVideo === sourceVideo).map((drop, i) => {
          const pos = mapToScreen(drop.sourceX, drop.sourceY);
          return (
            <div 
              key={i}
              className="absolute pointer-events-none flex items-center bg-gray-900/95 text-white rounded-xl shadow-2xl border border-gray-700/50 p-2 backdrop-blur-md"
              style={{ left: pos.x + 10, top: pos.y + 10 }}
            >
              <div 
                className="w-8 h-8 rounded-md border-2 border-white/20 shadow-inner mr-2"
                style={{ backgroundColor: drop.hex }}
              ></div>
              <div className="flex flex-col font-mono text-[10px] pr-1">
                <span className="font-bold text-gray-100 mb-0.5 tracking-wider">{drop.hex}</span>
                <span className="text-gray-400">RGB: <span className="text-gray-200">{drop.r},{drop.g},{drop.b}</span></span>
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const renderOcrBoxOverlay = (sourceVideo: "acceptance" | "emission", containerRef: React.RefObject<HTMLVideoElement | null>) => {
    if (!isOcrActive) return null;
    
    const video = containerRef.current;
    if (!video || video.readyState < 2) return null;
    
    const rect = video.getBoundingClientRect();
    const videoRatio = video.videoWidth / video.videoHeight;
    const containerRatio = rect.width / rect.height;

    let renderedWidth: number, renderedHeight: number, offsetX = 0, offsetY = 0;
    if (containerRatio > videoRatio) {
      renderedHeight = rect.height;
      renderedWidth = rect.height * videoRatio;
      offsetX = (rect.width - renderedWidth) / 2;
    } else {
      renderedWidth = rect.width;
      renderedHeight = rect.width / videoRatio;
      offsetY = (rect.height - renderedHeight) / 2;
    }

    const mapToScreen = (sx: number, sy: number) => ({
      x: (sx / video.videoWidth) * renderedWidth + offsetX,
      y: (sy / video.videoHeight) * renderedHeight + offsetY
    });

    const box = sourceVideo === "acceptance" ? ocrBoxAcceptance : ocrBoxEmission;
    const isDrawingBox = activeOcrBox?.sourceVideo === sourceVideo;
    
    return (
      <svg className="absolute top-4 left-4 w-[calc(100%-2rem)] h-[calc(100%-2rem)] pointer-events-none z-20">
        {box && (
          <rect
            x={mapToScreen(box.startX, box.startY).x}
            y={mapToScreen(box.startX, box.startY).y}
            width={mapToScreen(box.endX, box.endY).x - mapToScreen(box.startX, box.startY).x}
            height={mapToScreen(box.endX, box.endY).y - mapToScreen(box.startX, box.startY).y}
            fill="rgba(59, 130, 246, 0.2)"
            stroke="#3b82f6"
            strokeWidth="2"
            strokeDasharray="4 4"
          />
        )}
        {isDrawingBox && activeOcrBox && (
          <rect
            x={mapToScreen(Math.min(activeOcrBox.startX, activeOcrBox.endX), Math.min(activeOcrBox.startY, activeOcrBox.endY)).x}
            y={mapToScreen(Math.min(activeOcrBox.startX, activeOcrBox.endX), Math.min(activeOcrBox.startY, activeOcrBox.endY)).y}
            width={Math.abs(mapToScreen(activeOcrBox.endX, activeOcrBox.endY).x - mapToScreen(activeOcrBox.startX, activeOcrBox.startY).x)}
            height={Math.abs(mapToScreen(activeOcrBox.endX, activeOcrBox.endY).y - mapToScreen(activeOcrBox.startX, activeOcrBox.startY).y)}
            fill="rgba(59, 130, 246, 0.4)"
            stroke="#3b82f6"
            strokeWidth="2"
          />
        )}
      </svg>
    );
  };

  return (
    <div className={`${isSinglePlayerMode ? 'max-w-7xl' : 'max-w-[100rem]'} mx-auto px-6 py-6 pb-20 transition-all duration-500`}>
      {/* Eyedropper Tooltip */}
      {isEyedropperActive && hoverColor && (
        <div 
          className="fixed z-50 pointer-events-none flex items-center bg-gray-900/95 text-white rounded-xl shadow-2xl border border-gray-700/50 p-2 overflow-hidden backdrop-blur-md"
          style={{ left: hoverColor.x + 20, top: hoverColor.y + 20 }}
        >
          <div 
            className="w-10 h-10 rounded-md border-2 border-white/20 shadow-inner mr-3"
            style={{ backgroundColor: hoverColor.hex }}
          ></div>
          <div className="flex flex-col font-mono text-xs pr-2">
            <span className="font-bold text-gray-100 text-sm mb-0.5 tracking-wider">{hoverColor.hex}</span>
            <span className="text-gray-400">RGB: <span className="text-gray-200">{hoverColor.r}, {hoverColor.g}, {hoverColor.b}</span></span>
          </div>
        </div>
      )}

      {/* Title Header */}
      <div className="mb-6 flex items-start gap-5">
        <div className="flex-shrink-0 w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-600 via-purple-600 to-fuchsia-500 shadow-lg flex items-center justify-center transform hover:scale-105 transition-all duration-300 ring-4 ring-white">
          <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        </div>
        <div className="flex flex-col justify-center pt-0.5">
          <h2 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-gray-600 mb-1 tracking-tight flex items-center">
            VITO <span className="text-gray-400 font-medium text-2xl tracking-normal mx-3">Video Inspector Tool Observer</span><span className="text-xs text-purple-600 font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-purple-100/50 border border-purple-200 shadow-sm align-middle mt-1">v2.2</span>
          </h2>
          <p className="text-gray-500 text-sm md:text-base font-medium max-w-4xl leading-relaxed">
            Automatyczny audyt wideo: weryfikacja wizualna, parsowanie Excela (Copydeck) i porównywanie tekstu w locie (OCR).
          </p>
        </div>
      </div>

      {/* Top Toolbar */}
      <div className="mb-6 flex flex-wrap items-center gap-3 p-2 bg-white rounded-2xl border border-gray-100 shadow-sm">
        {/* ── Player Mode Toggle Switch ── */}
        <div className="flex items-center gap-3 flex-shrink-0 bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-200 shadow-sm">
          <span className={`text-sm font-semibold transition-colors cursor-pointer ${!isSinglePlayerMode ? 'text-gray-900' : 'text-gray-400'}`} onClick={() => { setIsSinglePlayerMode(false); }}>Dual</span>
          
          <button
            onClick={() => {
              const newMode = !isSinglePlayerMode;
              setIsSinglePlayerMode(newMode);
              if (newMode && diffMode) deactivateDiffMode();
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 ${
              isSinglePlayerMode ? 'bg-purple-600' : 'bg-gray-300'
            }`}
            title="Toggle player mode"
          >
            <span className="sr-only">Toggle player mode</span>
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                isSinglePlayerMode ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
          
          <span className={`text-sm font-semibold transition-colors cursor-pointer ${isSinglePlayerMode ? 'text-purple-600' : 'text-gray-400'}`} onClick={() => { setIsSinglePlayerMode(true); if (diffMode) deactivateDiffMode(); }}>Single</span>
        </div>

        {/* ── Diff Mode Toolbar ── */}
        <button
          onClick={() => diffMode ? deactivateDiffMode() : activateDiffMode()}
          disabled={(!acceptanceFile || !emissionFile) || isSinglePlayerMode}
          title={diffMode ? "Disable Diff Overlay" : "Enable Diff Overlay"}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed ${
            diffMode
              ? "bg-red-600 hover:bg-red-700 text-white shadow-red-600/20"
              : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20"
          }`}
        >
          {diffMode ? <EyeSlashIcon className="w-4 h-4" /> : <EyeIcon className="w-4 h-4" />}{diffMode ? "Diff ON" : "Diff OFF"}
          {isAnalyzing && diffMode && (
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
          )}
        </button>

        {isSinglePlayerMode && (
          <button
            onClick={runPlaystationQA}
            disabled={!acceptanceFile || isPsQaAnalyzing || !isBriefUploaded}
            title={!isBriefUploaded ? "Musisz najpierw wgrać LOC Brief!" : "Automated PS Element Check"}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed bg-green-600 hover:bg-green-700 text-white shadow-green-600/20`}
          >
            <EyeIcon className="w-4 h-4" />
            {isPsQaAnalyzing ? "Scanning..." : "PS Auto-Check"}
            {isPsQaAnalyzing && <span className="w-2 h-2 rounded-full bg-white animate-pulse" />}
          </button>
        )}

        {/* Brief Upload */}
        {isSinglePlayerMode && (
          <div className="relative">
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              ref={briefInputRef}
              onChange={handleBriefUpload}
            />
            <button
              onClick={() => briefInputRef.current?.click()}
              disabled={isUploadingBrief}
              title="Wgraj LOC Brief (.xlsx)"
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed ${
                isBriefUploaded ? 'bg-cyan-600 hover:bg-cyan-700 text-white shadow-cyan-600/20' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <DocumentTextIcon className="w-4 h-4" />
              {isUploadingBrief ? "Wgrywanie..." : isBriefUploaded ? "Brief Wgrany" : "Upload LOC Brief"}
            </button>
          </div>
        )}

        {/* Copydeck Upload */}
        {isSinglePlayerMode && (
          <div className="relative">
            <input
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              ref={copydeckInputRef}
              onChange={handleCopydeckUpload}
            />
            <button
              onClick={() => copydeckInputRef.current?.click()}
              disabled={isUploadingCopydeck}
              title="Upload Copydeck Excel"
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed ${
                copydeckData ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20' : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <DocumentTextIcon className="w-4 h-4" />
              {isUploadingCopydeck ? "Parsing..." : copydeckData ? "Copydeck Ready" : "Upload Copydeck"}
            </button>
          </div>
        )}
        
        {isSinglePlayerMode && (
          <button
            onClick={() => isQaMode ? deactivateQaMode() : activateQaMode()}
            disabled={!acceptanceFile}
            title="QA Technical Analysis"
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed ${
              isQaMode
                ? "bg-amber-600 hover:bg-amber-700 text-white shadow-amber-600/20"
                : "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-600/20"
            }`}
          >
            <EyeIcon className="w-4 h-4" />
            {isQaMode ? "QA ON" : "QA Analysis"}
            {isQaMode && <span className="w-2 h-2 rounded-full bg-white animate-pulse" />}
          </button>
        )}

        {/* OCR Top Toolbar Toggle */}
        {isSinglePlayerMode && (
          <button
            onClick={() => setIsOcrActive(!isOcrActive)}
            disabled={!acceptanceFile}
            title="Compare Copy (OCR)"
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-100 disabled:bg-gray-100 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed ${
              isOcrActive
                ? "bg-fuchsia-600 hover:bg-fuchsia-700 text-white shadow-fuchsia-600/20"
                : "bg-blue-600 hover:bg-blue-700 text-white shadow-blue-600/20"
            }`}
          >
            <DocumentTextIcon className="w-4 h-4" />
            {isOcrActive ? "OCR ON" : "Compare OCR"}
          </button>
        )}

        <button
          onClick={captureScreenshot}
          disabled={!acceptanceFile || (!isSinglePlayerMode && !emissionFile) || screenshotSaving}
          title="Save screenshot to Downloads"
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm bg-gray-800 hover:bg-gray-900 text-white transition-all disabled:opacity-40 disabled:cursor-not-allowed ml-auto"
        >
          <CameraIcon className="w-4 h-4" />
          {screenshotSaving ? "Saving…" : "Screenshot"}
        </button>
      </div>

      {/* ── Wipe / Diff Overlay Panel (visible only in diff mode) ── */}
      {diffMode && acceptanceFile && emissionFile && (
        <div id="wipe-diff-container" className="mb-6 bg-gray-950 rounded-2xl overflow-hidden border border-gray-800 shadow-xl">
          <div className="px-5 py-3 flex items-center justify-between border-b border-gray-800">
            <div className="flex items-center gap-3">
              <span className="text-sm font-semibold text-white">Wipe / Diff View</span>
              <span className="flex items-center gap-1.5 text-xs text-gray-400">
                <span className="w-3 h-3 rounded-sm bg-red-600 inline-block" /> Pewna różnica
                <span className="w-3 h-3 rounded-sm bg-yellow-400 inline-block ml-2" /> Do sprawdzenia
              </span>
            </div>
            <button
              onClick={() => analyzeCurrentFrame()}
              className="text-xs px-3 py-1 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors"
            >
              Odśwież klatkę
            </button>
          </div>

          {/* Wipe container — canvas-based, reads directly from main video refs.
               NO extra <video> elements here → no ref conflicts → no freeze on exit. */}
          <div
            ref={wipeContainerRef}
            className="relative w-full select-none flex justify-center bg-black"
            style={{ 
              aspectRatio: "16/9",
              cursor: "col-resize"
            }}
            onMouseDown={handleWipeMouseDown}
          >
            <canvas
              ref={wipeCanvasRef}
              className="block w-full h-full"
            />
          </div>

          {/* Wipe position slider */}
          <div className="px-5 py-3 border-t border-gray-800 flex items-center gap-4">
            <span className="text-xs text-gray-400 w-16">Pozycja:</span>
            <input
              type="range" min={0} max={100} step={0.5}
              value={wipePosition}
              onChange={(e) => setWipePosition(parseFloat(e.target.value))}
              className="flex-grow h-1.5 appearance-none bg-gray-700 rounded accent-white cursor-pointer"
            />
            <span className="text-xs text-gray-400 w-10 text-right font-mono">{wipePosition.toFixed(0)}%</span>
          </div>
        </div>
      )}

      {/* ── Diff Timestamps Panel ── */}
      {diffMode && diffTimestamps.length > 0 && (
        <div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <span className="text-sm font-semibold text-gray-800">Wykryte różnice ({diffTimestamps.length})</span>
            <span className="text-xs text-gray-400">Kliknij aby teleportować oba playery</span>
          </div>
          <div className="flex flex-wrap gap-2 p-4">
            {diffTimestamps.map((ts, i) => (
              <button
                key={i}
                onClick={() => teleportToTimestamp(ts.time)}
                title={ts.severity === "certain" ? "Pewna różnica" : "Do sprawdzenia"}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold border transition-all hover:scale-105 ${
                  ts.severity === "certain"
                    ? "bg-red-50 border-red-200 text-red-700 hover:bg-red-100"
                    : "bg-yellow-50 border-yellow-200 text-yellow-700 hover:bg-yellow-100"
                }`}
              >
                <span className={`w-2 h-2 rounded-full ${
                  ts.severity === "certain" ? "bg-red-500" : "bg-yellow-400"
                }`} />
                {formatTimecode(ts.time)}
              </button>
            ))}
          </div>
        </div>
      )}
      {/* ── No-diff info (diff mode active, no differences yet) ── */}
      {diffMode && diffTimestamps.length === 0 && isAnalyzing && (
        <div className="mb-6 px-5 py-3 bg-green-50 border border-green-200 rounded-2xl text-sm text-green-700 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          Analiza w toku — brak wykrytych różnic.
        </div>
      )}


      {/* ── Playstation QA Results Panel ── */}
      {isSinglePlayerMode && psQaMetadata && (
        <div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50">
            <span className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <span className="bg-blue-600 text-white text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider">PS Audit</span>
              Metadata Extracted
              {psQaResults?.scanTime && (
                <span className="ml-2 text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full font-medium border border-slate-200">
                  ⏱ {psQaResults.scanTime}
                </span>
              )}
            </span>
            <span className="text-xs font-mono text-slate-500 bg-white px-3 py-1 rounded-md border border-slate-200">
              Target: {psQaMetadata.country}
            </span>
          </div>
          
          <div className="p-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className={`p-4 rounded-xl border flex flex-col items-center justify-center text-center ${psQaResults ? (psQaResults.bing === 'FOUND' ? 'bg-green-50 border-green-200' : psQaResults.bing === 'INCORRECT' ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200') : 'bg-gray-50 border-gray-100'}`}>
              <span className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-semibold">BING</span>
              {psQaResults?.expected_bing_b64 && (
                <div className="h-12 w-full flex items-center justify-center mb-2">
                  <img src={psQaResults.expected_bing_b64} alt="Expected BING" className="max-h-full max-w-full object-contain mix-blend-multiply opacity-90 drop-shadow-sm" />
                </div>
              )}
              <span className="text-sm font-medium text-gray-900">{psQaMetadata.bing}</span>
              {psQaResults && (
                <span className={`mt-2 px-3 py-1 rounded-full text-[11px] font-bold ${psQaResults.bing === 'FOUND' ? 'bg-green-100 text-green-700' : psQaResults.bing === 'INCORRECT' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                  {psQaResults.bing === 'FOUND' ? "✅ FOUND" : psQaResults.bing === 'INCORRECT' ? "⚠️ INCORRECT VERSION" : "❌ CRITICAL: MISSING"}
                </span>
              )}
            </div>
            
            <div className={`p-4 rounded-xl border flex flex-col items-center justify-center text-center ${psQaResults ? (psQaResults.rating === 'FOUND' ? 'bg-green-50 border-green-200' : psQaResults.rating === 'INCORRECT' ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200') : 'bg-gray-50 border-gray-100'}`}>
              <span className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-semibold">RATING</span>
              {psQaResults?.expected_rating_b64 && (
                <div className="h-12 w-full flex items-center justify-center mb-2">
                  <img src={psQaResults.expected_rating_b64} alt="Expected RATING" className="max-h-full max-w-full object-contain mix-blend-multiply opacity-90 drop-shadow-sm" />
                </div>
              )}
              <span className="text-sm font-medium text-gray-900">{psQaMetadata.rating}</span>
              {psQaResults && (
                <span className={`mt-2 px-3 py-1 rounded-full text-[11px] font-bold ${psQaResults.rating === 'FOUND' ? 'bg-green-100 text-green-700' : psQaResults.rating === 'INCORRECT' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                  {psQaResults.rating === 'FOUND' ? "✅ FOUND" : psQaResults.rating === 'INCORRECT' ? "⚠️ INCORRECT VERSION" : "❌ CRITICAL: MISSING"}
                </span>
              )}
            </div>
            
            <div className={`p-4 rounded-xl border flex flex-col items-center justify-center text-center ${psQaResults ? (psQaResults.bong === 'FOUND' ? 'bg-green-50 border-green-200' : psQaResults.bong === 'INCORRECT' ? 'bg-amber-50 border-amber-200' : 'bg-red-50 border-red-200') : 'bg-gray-50 border-gray-100'}`}>
              <span className="text-xs text-gray-500 uppercase tracking-wider mb-2 font-semibold">BONG</span>
              {psQaResults?.expected_bong_b64 && (
                <div className="h-12 w-full flex items-center justify-center mb-2">
                  <img src={psQaResults.expected_bong_b64} alt="Expected BONG" className="max-h-full max-w-full object-contain mix-blend-multiply opacity-90 drop-shadow-sm" />
                </div>
              )}
              <span className="text-sm font-medium text-gray-900">{psQaMetadata.bong}</span>
              {psQaResults && (
                <span className={`mt-2 px-3 py-1 rounded-full text-[11px] font-bold ${psQaResults.bong === 'FOUND' ? 'bg-green-100 text-green-700' : psQaResults.bong === 'INCORRECT' ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}`}>
                  {psQaResults.bong === 'FOUND' ? "✅ FOUND" : psQaResults.bong === 'INCORRECT' ? "⚠️ INCORRECT VERSION" : "❌ CRITICAL: MISSING"}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Copydeck Results Panel ── */}
      {copydeckData && (
        <div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-indigo-50">
            <span className="text-sm font-bold text-indigo-900 flex items-center gap-2">
              <span className="bg-indigo-600 text-white text-[10px] px-2 py-0.5 rounded-full uppercase tracking-wider">Excel Parser</span>
              Copydeck Loaded Successfully
            </span>
            <span className="text-xs font-mono text-indigo-700 bg-white px-3 py-1 rounded-md border border-indigo-200">
              Languages: {copydeckData.languages.length}
            </span>
          </div>
          
          <div className="p-5 flex gap-2 flex-wrap">
            {copydeckData.languages.map((lang: string, idx: number) => (
              <span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full border border-gray-200">
                {lang}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── QA Technical Analysis Timestamps Panel ── */}
      {isQaMode && qaDefects.length > 0 && (
        <div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span className="text-sm font-semibold text-gray-800">QA Technical Analysis ({qaDefects.length} defects)</span>
            <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
              <span className="flex items-center gap-1"><span className="text-[10px]">⬛️</span> Blackness</span>
              <span className="flex items-center gap-1"><span className="text-[10px]">❄️</span> Freeze</span>
              <span className="flex items-center gap-1"><span className="text-[10px]">⚠️</span> Frame Skip</span>
              <span className="hidden sm:inline-block ml-2 border-l border-gray-200 pl-3 text-gray-400">Click to jump to time</span>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 p-4">
            {qaDefects.map((ts, i) => (
              <button
                key={i}
                onClick={() => handleSeek(ts.time)}
                title={ts.type}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-semibold border transition-all hover:scale-105 ${
                  ts.type === "black"
                    ? "bg-gray-800 border-gray-900 text-white hover:bg-gray-700"
                    : ts.type === "freeze"
                    ? "bg-blue-50 border-blue-200 text-blue-700 hover:bg-blue-100"
                    : "bg-yellow-50 border-yellow-200 text-yellow-700 hover:bg-yellow-100"
                }`}
              >
                <span>{ts.type === "black" ? "⬛️" : ts.type === "freeze" ? "❄️" : "⚠️"}</span>
                {formatTimecode(ts.time)}
              </button>
            ))}
          </div>
        </div>
      )}
      {isQaMode && qaDefects.length === 0 && (
        <div className="mb-6 px-5 py-3 bg-blue-50 border border-blue-200 rounded-2xl text-sm text-blue-700 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
          QA Analysis active — no defects detected.
        </div>
      )}

      {/* Video Panels Area */}
      <div className={`grid grid-cols-1 ${isSinglePlayerMode ? '' : 'lg:grid-cols-2'} gap-6 mb-8`}>
        
        {/* Acceptance Video Panel */}
        <div
          onDragEnter={(e) => handleDragEnter(e, "acceptance")}
          onDragOver={handleDragOver}
          onDragLeave={(e) => handleDragLeave(e, "acceptance")}
          onDrop={(e) => handleDrop(e, "acceptance")}
          className={`bg-white rounded-2xl shadow-sm border overflow-hidden transition-all duration-200 ${
            isDraggingAcceptance ? "border-green-500 ring-4 ring-green-100 scale-[1.01]" : "border-gray-200"
          } ${isSinglePlayerMode ? "max-w-[90%] mx-auto w-full" : ""}`}
        >
          {/* Header Panel */}
          <div className={`px-6 py-4 border-b border-gray-100 flex justify-between items-center ${
            isSinglePlayerMode ? 'bg-purple-50/50' : 'bg-green-50/50'
          }`}>
            <div>
              <h3 className={`font-semibold ${isSinglePlayerMode ? 'text-purple-800' : 'text-green-800'}`}>
                {isSinglePlayerMode ? 'Video Preview (Inspection)' : 'Acceptance (Reference)'}
              </h3>
              {acceptanceFile && (
                <p className="text-xs text-gray-500 flex items-center mt-0.5" title={acceptanceFile.name}>
                  <span className="break-all">{acceptanceFile.name}</span>
                  <span className="flex-shrink-0 ml-1.5 font-medium whitespace-nowrap">
                    • {formatFileSize(acceptanceFile.size)}
                    {accDimensions && ` • ${accDimensions.width}x${accDimensions.height}`}
                    {acceptanceFile.conversionTime && ` • Konwersja: ${acceptanceFile.conversionTime}s`}
                  </span>
                </p>
              )}
            </div>
            {acceptanceFile && (
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                isSinglePlayerMode ? 'bg-purple-100 text-purple-800' : 'bg-green-100 text-green-800'
              }`}>
                {acceptanceFile.isLocal ? "Local" : "Server"}
              </span>
            )}
          </div>

          {/* Player Container */}
          <div id="acceptance-container" className="p-4 bg-gray-50/40 relative aspect-video flex items-center justify-center">
            {acceptanceLoading && (
              <div className="absolute inset-0 z-30 bg-gray-950/85 backdrop-blur-sm flex flex-col items-center justify-center text-white p-6 text-center transition-all duration-200">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-green-500 border-t-transparent mb-4 shadow-lg shadow-green-500/20"></div>
                <p className="font-semibold text-base text-gray-100 tracking-wide mb-3">{acceptanceLoadingMessage || "Processing video..."}</p>
                {acceptanceProgress !== null && acceptanceProgress > 0 && (
                  <div className="w-full max-w-xs bg-gray-800 rounded-full h-2.5 mb-3 overflow-hidden border border-gray-700 shadow-inner">
                    <div 
                      className="bg-green-500 h-full rounded-full transition-all duration-300 ease-out shadow-[0_0_8px_rgba(34,197,94,0.6)]" 
                      style={{ width: `${acceptanceProgress}%` }}
                    ></div>
                  </div>
                )}
                <p className="text-xs text-gray-400 font-mono bg-gray-900/60 px-3 py-1 rounded-full border border-gray-800/40">
                  Optymalne transkodowanie w tle (CPU z limitem wątków)
                </p>
              </div>
            )}

            {acceptanceError && (
              <div className="absolute inset-0 z-30 bg-red-50 p-6 flex flex-col items-center justify-center text-center">
                <p className="text-red-600 font-semibold mb-2">Video Loading Error</p>
                <p className="text-xs text-red-500 max-w-sm mb-4">{acceptanceError}</p>
                <button
                  onClick={() => setAcceptanceError(null)}
                  className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                >
                  Zamknij
                </button>
              </div>
            )}

            {acceptanceFile ? (
              <video
                ref={acceptanceVideoRef}
                className={`w-full h-full object-contain bg-black rounded-lg ${(isEyedropperActive || isRulerActive || isOcrActive) && !isPlaying ? "cursor-crosshair" : ""}`}
                src={acceptanceFile.url}
                crossOrigin="anonymous"
                preload="auto"
                onLoadedMetadata={(e) => {
                  setAccDimensions({ width: e.currentTarget.videoWidth, height: e.currentTarget.videoHeight });
                }}
                onMouseDown={(e) => handleVideoMouseDown(e, acceptanceVideoRef)}
                onMouseMove={(e) => handleVideoMouseMove(e, acceptanceVideoRef)}
                onMouseUp={handleVideoMouseUp}
                onMouseLeave={handleVideoMouseUp}
                onError={() => {
                  setAcceptanceError("Failed to load video stream from server (np. file expired in DEV mode or connection lost).");
                }}
              />
            ) : (
              <div className="w-full h-full border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center p-6 text-center text-gray-400 bg-white">
                <ArrowUpTrayIcon className="w-12 h-12 text-gray-300 mb-3" />
                <p className="text-sm font-semibold text-gray-700">Drag and drop Acceptance video</p>
                <p className="text-xs text-gray-400 mt-1">Supports MP4, MOV, MXF</p>
              </div>
            )}
            {renderRulerOverlay("acceptance", acceptanceVideoRef)}
            {renderEyedropperOverlay("acceptance", acceptanceVideoRef)}
            {renderOcrBoxOverlay("acceptance", acceptanceVideoRef)}
          </div>

          {/* Volume control */}
          <div className="px-6 py-3 bg-gray-50/50 border-t border-gray-100 flex items-center space-x-3">
            <button
              disabled={!acceptanceFile}
              onClick={() => {
                if (acceptanceVolume > 0) setAcceptanceVolume(0);
                else setAcceptanceVolume(1);
              }}
              className="p-1 text-gray-500 hover:text-gray-700 disabled:opacity-40"
            >
              {acceptanceVolume === 0 || isMuted ? (
                <SpeakerXMarkIcon className="w-4 h-4 text-gray-400" />
              ) : (
                <SpeakerWaveIcon className="w-4 h-4" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={isMuted ? 0 : acceptanceVolume}
              onChange={(e) => setAcceptanceVolume(parseFloat(e.target.value))}
              disabled={!acceptanceFile}
              className="w-28 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-green-600 disabled:opacity-40"
            />
            <span className="text-[10px] text-gray-400 w-8 tabular-nums font-semibold">
              {Math.round((isMuted ? 0 : acceptanceVolume) * 100)}%
            </span>
            <div className="ml-auto flex items-center space-x-1 text-xs text-gray-500 font-mono bg-white px-2 py-1 rounded border border-gray-200">
              <label className="font-semibold text-gray-600 mr-1">Trim</label>
              <button 
                onClick={() => setAcceptanceTrim(t => Math.max(0, t - 0.04))}
                className="w-5 h-5 flex items-center justify-center bg-gray-100 rounded hover:bg-gray-200 text-gray-700"
                disabled={!acceptanceFile}
              >-</button>
              <input
                type="number"
                min="0"
                step="0.04"
                value={Number(acceptanceTrim.toFixed(2))}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 0;
                  setAcceptanceTrim(Math.round(val / 0.04) * 0.04);
                }}
                disabled={!acceptanceFile}
                className="w-16 h-6 px-1 text-center bg-transparent focus:outline-none focus:ring-1 focus:ring-red-500 rounded disabled:opacity-40"
              />
              <button 
                onClick={() => setAcceptanceTrim(t => t + 0.04)}
                className="w-5 h-5 flex items-center justify-center bg-gray-100 rounded hover:bg-gray-200 text-gray-700"
                disabled={!acceptanceFile}
              >+</button>
              <span className="ml-1">s</span>
            </div>
          </div>
        </div>

        {/* Emission Video Panel */}
        {!isSinglePlayerMode && (
        <div
          onDragEnter={(e) => handleDragEnter(e, "emission")}
          onDragOver={handleDragOver}
          onDragLeave={(e) => handleDragLeave(e, "emission")}
          onDrop={(e) => handleDrop(e, "emission")}
          className={`bg-white rounded-2xl shadow-sm border overflow-hidden transition-all duration-200 ${
            isDraggingEmission ? "border-red-500 ring-4 ring-red-100 scale-[1.01]" : "border-gray-200"
          }`}
        >
          {/* Header Panel */}
          <div className="px-6 py-4 border-b border-gray-100 bg-red-50/50 flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-red-800">Emission</h3>
              {emissionFile && (
                <p className="text-xs text-gray-500 flex items-center mt-0.5" title={emissionFile.name}>
                  <span className="break-all">{emissionFile.name}</span>
                  <span className="flex-shrink-0 ml-1.5 font-medium whitespace-nowrap">
                    • {formatFileSize(emissionFile.size)}
                    {emDimensions && ` • ${emDimensions.width}x${emDimensions.height}`}
                    {emissionFile.conversionTime && ` • Konwersja: ${emissionFile.conversionTime}s`}
                  </span>
                </p>
              )}
            </div>
            {emissionFile && (
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-800 uppercase">
                {emissionFile.isLocal ? "Local" : "Server"}
              </span>
            )}
          </div>

          {/* Player Container */}
          <div id="emission-container" className="p-4 bg-gray-50/40 relative aspect-video flex items-center justify-center">
            {emissionLoading && (
              <div className="absolute inset-0 z-30 bg-gray-950/85 backdrop-blur-sm flex flex-col items-center justify-center text-white p-6 text-center transition-all duration-200">
                <div className="animate-spin rounded-full h-12 w-12 border-4 border-red-500 border-t-transparent mb-4 shadow-lg shadow-red-500/20"></div>
                <p className="font-semibold text-base text-gray-100 tracking-wide mb-3">{emissionLoadingMessage || "Processing video..."}</p>
                {emissionProgress !== null && emissionProgress > 0 && (
                  <div className="w-full max-w-xs bg-gray-800 rounded-full h-2.5 mb-3 overflow-hidden border border-gray-700 shadow-inner">
                    <div 
                      className="bg-red-500 h-full rounded-full transition-all duration-300 ease-out shadow-[0_0_8px_rgba(239,68,68,0.6)]" 
                      style={{ width: `${emissionProgress}%` }}
                    ></div>
                  </div>
                )}
                <p className="text-xs text-gray-400 font-mono bg-gray-900/60 px-3 py-1 rounded-full border border-gray-800/40">
                  Optymalne transkodowanie w tle (CPU z limitem wątków)
                </p>
              </div>
            )}

            {emissionError && (
              <div className="absolute inset-0 z-30 bg-red-50 p-6 flex flex-col items-center justify-center text-center">
                <p className="text-red-600 font-semibold mb-2">Video Loading Error</p>
                <p className="text-xs text-red-500 max-w-sm mb-4">{emissionError}</p>
                <button
                  onClick={() => setEmissionError(null)}
                  className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-colors"
                >
                  Zamknij
                </button>
              </div>
            )}

            {emissionFile ? (
              <video
                ref={emissionVideoRef}
                className={`w-full h-full object-contain bg-black rounded-lg ${(isEyedropperActive || isRulerActive || isOcrActive) && !isPlaying ? "cursor-crosshair" : ""}`}
                src={emissionFile.url}
                crossOrigin="anonymous"
                preload="auto"
                onLoadedMetadata={(e) => {
                  setEmDimensions({ width: e.currentTarget.videoWidth, height: e.currentTarget.videoHeight });
                }}
                onMouseDown={(e) => handleVideoMouseDown(e, emissionVideoRef)}
                onMouseMove={(e) => handleVideoMouseMove(e, emissionVideoRef)}
                onMouseUp={handleVideoMouseUp}
                onMouseLeave={handleVideoMouseUp}
                onError={() => {
                  setEmissionError("Failed to load video stream from server (np. file expired in DEV mode or connection lost).");
                }}
              />
            ) : (
              <div className="w-full h-full border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center p-6 text-center text-gray-400 bg-white">
                <ArrowUpTrayIcon className="w-12 h-12 text-gray-300 mb-3" />
                <p className="text-sm font-semibold text-gray-700">Drag and drop Emission video</p>
                <p className="text-xs text-gray-400 mt-1">Supports MP4, MOV, MXF</p>
              </div>
            )}
            {renderRulerOverlay("emission", emissionVideoRef)}
            {renderEyedropperOverlay("emission", emissionVideoRef)}
            {renderOcrBoxOverlay("emission", emissionVideoRef)}
          </div>

          {/* Volume control */}
          <div className="px-6 py-3 bg-gray-50/50 border-t border-gray-100 flex items-center space-x-3">
            <button
              disabled={!emissionFile}
              onClick={() => {
                if (emissionVolume > 0) setEmissionVolume(0);
                else setEmissionVolume(1);
              }}
              className="p-1 text-gray-500 hover:text-gray-700 disabled:opacity-40"
            >
              {emissionVolume === 0 || isMuted ? (
                <SpeakerXMarkIcon className="w-4 h-4 text-gray-400" />
              ) : (
                <SpeakerWaveIcon className="w-4 h-4" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={isMuted ? 0 : emissionVolume}
              onChange={(e) => setEmissionVolume(parseFloat(e.target.value))}
              disabled={!emissionFile}
              className="w-28 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-red-600 disabled:opacity-40"
            />
            <span className="text-[10px] text-gray-400 w-8 tabular-nums font-semibold">
              {Math.round((isMuted ? 0 : emissionVolume) * 100)}%
            </span>
            <div className="ml-auto flex items-center space-x-1 text-xs text-gray-500 font-mono bg-white px-2 py-1 rounded border border-gray-200">
              <label className="font-semibold text-gray-600 mr-1">Trim</label>
              <button 
                onClick={() => setEmissionTrim(t => Math.max(0, t - 0.04))}
                className="w-5 h-5 flex items-center justify-center bg-gray-100 rounded hover:bg-gray-200 text-gray-700"
                disabled={!emissionFile}
              >-</button>
              <input
                type="number"
                min="0"
                step="0.04"
                value={Number(emissionTrim.toFixed(2))}
                onChange={(e) => {
                  const val = parseFloat(e.target.value) || 0;
                  setEmissionTrim(Math.round(val / 0.04) * 0.04);
                }}
                disabled={!emissionFile}
                className="w-16 h-6 px-1 text-center bg-transparent focus:outline-none focus:ring-1 focus:ring-red-500 rounded disabled:opacity-40"
              />
              <button 
                onClick={() => setEmissionTrim(t => t + 0.04)}
                className="w-5 h-5 flex items-center justify-center bg-gray-100 rounded hover:bg-gray-200 text-gray-700"
                disabled={!emissionFile}
              >+</button>
              <span className="ml-1">s</span>
            </div>
          </div>
        </div>
        )}
      </div>

      {/* Synchronized Playback Control Dashboard */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          
          {/* Timeline and Seek Bar */}
          <div className="flex-grow flex items-center space-x-4">
            <div className="flex flex-col items-end w-20 flex-shrink-0">
              <span className="text-sm text-gray-700 font-mono font-medium">
                {formatTimecode(currentTime)}
              </span>
              <span className="text-[10px] text-gray-400 font-mono">
                {formatTime(currentTime)}
              </span>
            </div>
            <input
              type="range"
              min="0"
              max={duration || 100}
              step="0.01"
              value={currentTime}
              onChange={(e) => handleSeek(parseFloat(e.target.value))}
              disabled={!acceptanceFile && !emissionFile}
              className="flex-grow h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600 disabled:opacity-40"
            />
            <div className="flex flex-col items-start w-20 flex-shrink-0">
              <span className="text-sm text-gray-700 font-mono font-medium">
                {formatTimecode(duration)}
              </span>
              <span className="text-[10px] text-gray-400 font-mono">
                {formatTime(duration)}
              </span>
            </div>
          </div>

          {/* Navigation Control Buttons */}
          <div className="flex items-center justify-center space-x-3 flex-shrink-0">
            {/* Step Backward */}
            <button
              onClick={() => handleStep(-1)}
              disabled={!acceptanceFile && !emissionFile}
              className="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-gray-100"
              title="-1 Klatka"
            >
              <ChevronLeftIcon className="w-5 h-5" />
            </button>

            {/* Play/Pause Button */}
            <button
              onClick={togglePlayPause}
              disabled={!acceptanceFile && !emissionFile}
              className={`w-12 h-12 flex items-center justify-center text-white rounded-full transition-all shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                !acceptanceFile && !emissionFile
                  ? "bg-gray-300 shadow-none cursor-not-allowed"
                  : "bg-blue-600 hover:bg-blue-700 shadow-blue-600/10"
              }`}
              title="Odtwarzaj / Pauza"
            >
              {isPlaying ? <PauseIcon className="w-5 h-5" /> : <PlayIcon className="w-5 h-5 ml-0.5" />}
            </button>

            {/* Step Forward */}
            <button
              onClick={() => handleStep(1)}
              disabled={!acceptanceFile && !emissionFile}
              className="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-gray-100"
              title="+1 Klatka"
            >
              <ChevronRightIcon className="w-5 h-5" />
            </button>

            {/* Stop Button */}
            <button
              onClick={handleStop}
              disabled={!acceptanceFile && !emissionFile}
              className="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-gray-100"
              title="Zatrzymaj"
            >
              <StopIcon className="w-5 h-5" />
            </button>

            {/* Eyedropper Toggle */}
            <div className="w-px h-6 bg-gray-300 mx-2"></div>
            <button
              onClick={() => {
                setIsEyedropperActive(!isEyedropperActive);
                if (isEyedropperActive) {
                  setHoverColor(null);
                  setEyedropperDrops([]);
                }
              }}
              disabled={!acceptanceFile && !emissionFile}
              className={`w-10 h-10 flex items-center justify-center rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-transparent ${
                isEyedropperActive 
                  ? "bg-indigo-100 text-indigo-700 hover:bg-indigo-200" 
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              title={isEyedropperActive ? "Wyłącz próbnik koloru (Kroplomierz)" : "Włącz próbnik koloru (Kroplomierz, aktywny na pauzie)"}
            >
              <EyeDropperIcon className="w-5 h-5" />
            </button>

            {/* Ruler Toggle */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => {
                  setIsRulerActive(!isRulerActive);
                  if (isRulerActive) {
                    setRulerLines([]);
                    setActiveRulerLine(null);
                  }
                }}
                disabled={!acceptanceFile && !emissionFile}
                className={`w-10 h-10 flex items-center justify-center rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-transparent ${
                  isRulerActive 
                    ? "bg-blue-100 text-blue-700 hover:bg-blue-200" 
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
                title={isRulerActive ? "Wyłącz miarkę (Linijka)" : "Włącz miarkę pikseli (Linijka, aktywna na pauzie)"}
              >
                <RulerIcon className="w-5 h-5" />
              </button>
              {isRulerActive && (
                <input
                  type="color"
                  value={rulerColor}
                  onChange={(e) => setRulerColor(e.target.value)}
                  className="w-6 h-6 p-0 border-0 rounded-full overflow-hidden cursor-pointer bg-transparent"
                  title="Select ruler color"
                />
              )}
            </div>

            {/* OCR Compare Copy Toggle */}
            <button
              onClick={() => setIsOcrActive(!isOcrActive)}
              disabled={!acceptanceFile && !emissionFile}
              className={`w-10 h-10 flex items-center justify-center rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-transparent ${
                isOcrActive 
                  ? "bg-purple-100 text-purple-700 hover:bg-purple-200" 
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              title={isOcrActive ? "Wyłącz porównanie tekstu (OCR)" : "Włącz porównanie tekstu (OCR)"}
            >
              <DocumentTextIcon className="w-5 h-5" />
            </button>

            {/* Report Builder Toggle */}
            <div className="w-px h-6 bg-gray-300 mx-2"></div>
            <button
              onClick={() => handleCaptureReport()}
              disabled={capturingReport || (!acceptanceFile && !emissionFile)}
              className={`w-10 h-10 flex items-center justify-center rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-transparent ${
                capturingReport 
                  ? "bg-amber-100 text-amber-700 animate-pulse" 
                  : "bg-amber-50 text-amber-600 hover:bg-amber-100 border border-amber-200/50"
              }`}
              title="Add current view to PDF Report"
            >
              <CameraIcon className="w-5 h-5" />
            </button>
            <button
              onClick={() => setIsReportModalOpen(true)}
              className="px-3 h-10 flex items-center gap-2 rounded-xl transition-colors bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 text-sm font-semibold"
            >
              Raport
              {reportItems.length > 0 && (
                <span className="bg-amber-500 text-white text-[10px] px-1.5 py-0.5 rounded-full font-bold">
                  {reportItems.length}
                </span>
              )}
            </button>

            <div className="flex-1"></div>

            {/* Analyze current frame (only visible in diff mode) */}
            {diffMode && (
              <button
                onClick={() => analyzeCurrentFrame()}
                title="Analizuj bieżącą klatkę"
                className="w-10 h-10 flex items-center justify-center bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-xl transition-colors"
              >
                <EyeIcon className="w-5 h-5" />
              </button>
            )}

            {/* Refresh Button */}
            <button
              onClick={handleRefresh}
              disabled={!acceptanceFile && !emissionFile}
              className="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-gray-100"
              title="Odśwież / Przeładuj"
            >
              <ArrowPathIcon className="w-5 h-5" />
            </button>

            <div className="h-6 w-px bg-gray-200 mx-1"></div>

            {/* Clear Button */}
            <button
              onClick={handleClear}
              disabled={!acceptanceFile && !emissionFile}
              className="w-10 h-10 flex items-center justify-center bg-gray-100 hover:bg-red-50 hover:text-red-600 text-gray-600 rounded-xl transition-colors disabled:opacity-40 disabled:hover:bg-gray-100"
              title="Wyczyść odtwarzacze"
            >
              <XMarkIcon className="w-5 h-5" />
            </button>

            <div className="h-6 w-px bg-gray-200 mx-1"></div>

            {/* Global Mute Button */}
            <button
              onClick={() => setIsMuted(!isMuted)}
              disabled={!acceptanceFile && !emissionFile}
              className={`w-10 h-10 flex items-center justify-center rounded-xl transition-colors disabled:opacity-40 ${
                isMuted ? "bg-red-50 text-red-600" : "bg-gray-100 hover:bg-gray-200 text-gray-600"
              }`}
              title="Wycisz wszystko"
            >
            </button>
          </div>
        </div>
      </div>

      {/* OCR / Compare Copy Panel */}
      {isOcrActive && (
        <div id="ocr-panel-container" className="mt-8 bg-white rounded-2xl shadow-sm border border-purple-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-purple-100 bg-purple-50/50 flex justify-between items-center">
            <h3 className="font-semibold text-purple-900 flex items-center gap-2">
              <DocumentTextIcon className="w-5 h-5" /> Compare Copy (OCR)
            </h3>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <span className="text-xs text-purple-700 font-semibold">Czułość kontrastu:</span>
                <input 
                  type="range" 
                  min="0" max="127" 
                  value={ocrContrast} 
                  onChange={(e) => setOcrContrast(Number(e.target.value))}
                  className="w-24 accent-purple-600"
                  title={`Kontrast (0 = oryginalny, 127 = binarny): ${ocrContrast}`}
                />
              </div>

              <div className="w-px h-4 bg-purple-200 mx-1"></div>

              <label className="flex items-center gap-1.5 text-xs text-purple-800 cursor-pointer hover:bg-purple-100 px-2 py-1 rounded transition-colors">
                <input 
                  type="checkbox" 
                  checked={ocrInvertColors}
                  onChange={(e) => setOcrInvertColors(e.target.checked)}
                  className="rounded text-purple-600 focus:ring-purple-500 w-3 h-3 cursor-pointer"
                />
                Jasny tekst na ciemnym tle (odwróć kolory)
              </label>
              
              <div className="w-px h-4 bg-purple-200 mx-1"></div>

              <span className="text-xs font-semibold text-purple-700">Język:</span>
              <div className="flex items-center gap-1">
                <select 
                  value={ocrLanguage}
                  onChange={(e) => setOcrLanguage(e.target.value)}
                  className="text-xs border-purple-200 rounded px-2 py-1 bg-white focus:ring-purple-500 text-purple-900 cursor-pointer"
                >
                  <option value="eng+pol">Auto (Angielski + Polski)</option>
                  {Object.entries(LANGUAGE_TO_TESSERACT)
                    .map(([name, code]) => ({ name, code }))
                    .filter((val, index, self) => index === self.findIndex((t) => t.name === val.name))
                    .map(({ name, code }) => (
                    <option key={name} value={code}>{name}</option>
                  ))}
                  <option value="custom">Inny (Wpisz kod ISO)...</option>
                </select>
                {ocrLanguage === "custom" && (
                  <input
                    type="text"
                    value={ocrCustomLanguage}
                    onChange={(e) => setOcrCustomLanguage(e.target.value.toLowerCase().replace(/[^a-z]/g, ''))}
                    placeholder="np. ell"
                    className="w-16 text-xs border-purple-200 rounded px-2 py-1 focus:ring-purple-500 text-purple-900"
                    maxLength={3}
                    title="Podaj 3-literowy kod języka (ISO 639-2)"
                  />
                )}
              </div>
            </div>
          </div>
          
          {/* Live Camera Feed Previews */}
          {(ocrPreviewAcceptance || ocrPreviewEmission) && (
            <div className="bg-gray-900 border-b border-gray-800 p-6 flex flex-col md:flex-row gap-6">
              {ocrPreviewAcceptance && (
                <div className="flex-1 flex flex-col gap-2">
                  <div className="flex justify-between items-center px-1">
                    <span className="text-[10px] uppercase font-bold text-green-400 tracking-wider flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                      LIVE OCR FEED (ACCEPTANCE)
                    </span>
                  </div>
                  <div className="w-full flex items-center justify-center bg-black rounded-xl border border-gray-700 shadow-inner overflow-hidden" style={{ minHeight: "150px", maxHeight: "350px" }}>
                    <img src={ocrPreviewAcceptance} alt="Preview Acceptance" className="max-w-full max-h-full object-contain" />
                  </div>
                </div>
              )}
              {ocrPreviewEmission && (
                <div className="flex-1 flex flex-col gap-2">
                  <div className="flex justify-between items-center px-1">
                    <span className="text-[10px] uppercase font-bold text-red-400 tracking-wider flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                      LIVE OCR FEED (EMISSION)
                    </span>
                  </div>
                  <div className="w-full flex items-center justify-center bg-black rounded-xl border border-gray-700 shadow-inner overflow-hidden" style={{ minHeight: "150px", maxHeight: "350px" }}>
                    <img src={ocrPreviewEmission} alt="Preview Emission" className="max-w-full max-h-full object-contain" />
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Brief Input */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-gray-700">Skopiowany Brief (wklej tutaj)</label>
                {copydeckData && copydeckData.languages && copydeckData.languages.length > 0 && (
                  <select
                    className="text-xs border-indigo-200 rounded px-2 py-1 bg-indigo-50 focus:ring-indigo-500 text-indigo-900 cursor-pointer"
                    value={selectedCopydeckLanguage}
                    onChange={(e) => {
                      const lang = e.target.value;
                      setSelectedCopydeckLanguage(lang);
                      if (lang && copydeckData.data[lang]) {
                        // Extract all target values for this language
                        const translations = Object.values(copydeckData.data[lang]) as string[];
                        setAvailableCopydeckLines(translations);
                        
                        if (translations.length > 0) {
                          setOcrBriefText(translations[0]); // domyślnie pierwszy wiersz
                        } else {
                          setOcrBriefText("");
                        }
                        
                        // Auto-sync OCR language with copydeck language if we have a match
                        if (LANGUAGE_TO_TESSERACT[lang]) {
                          setOcrLanguage(LANGUAGE_TO_TESSERACT[lang]);
                        }
                      } else {
                        setAvailableCopydeckLines([]);
                        setOcrBriefText("");
                      }
                    }}
                  >
                    <option value="">-- Wypełnij z Copydecku --</option>
                    {copydeckData.languages.map((l: string) => (
                      <option key={l} value={l}>{l}</option>
                    ))}
                  </select>
                )}
              </div>
              <textarea 
                value={ocrBriefText}
                onChange={(e) => setOcrBriefText(e.target.value)}
                placeholder="Wklej tekst z briefu (PPTX/Word) do porównania..."
                className="w-full h-32 p-3 text-sm border border-gray-300 rounded-lg focus:ring-purple-500 focus:border-purple-500 resize-none font-mono"
              />
            </div>
            
            {/* OCR Extracted Acceptance */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-green-700">Text from Acceptance video</label>
                {ocrBoxAcceptance ? (
                  <span className="text-[10px] bg-green-100 text-green-800 px-2 py-0.5 rounded font-mono">ZAZNACZONO OBSZAR</span>
                ) : (
                  <span className="text-[10px] text-gray-400 font-mono">ZAZNACZ OBSZAR MYSZKĄ</span>
                )}
              </div>
              
              <textarea 
                value={ocrTextAcceptance}
                readOnly
                placeholder="Text extracted from Acceptance video will appear here..."
                className="w-full h-32 p-3 text-sm border border-gray-300 bg-gray-50 rounded-lg focus:outline-none resize-none font-mono"
              />
            </div>
            
            {/* OCR Extracted Emission */}
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-semibold text-red-700">Text from Emission video</label>
                {ocrBoxEmission ? (
                  <span className="text-[10px] bg-red-100 text-red-800 px-2 py-0.5 rounded font-mono">ZAZNACZONO OBSZAR</span>
                ) : (
                  <span className="text-[10px] text-gray-400 font-mono">ZAZNACZ OBSZAR MYSZKĄ</span>
                )}
              </div>
              
              <textarea 
                value={ocrTextEmission}
                readOnly
                placeholder="Text extracted from Emission video will appear here..."
                className="w-full h-32 p-3 text-sm border border-gray-300 bg-gray-50 rounded-lg focus:outline-none resize-none font-mono"
              />
            </div>
          </div>
          
          {/* Selectable Copydeck Lines - Full Width */}
          {availableCopydeckLines.length > 0 && (
            <div className="px-6 pb-2 -mt-2">
              <span className="text-[10px] uppercase font-bold text-gray-500 mb-2 block">Wybierz wiersz z pliku Excel (Copydeck):</span>
              <div className="flex gap-3 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent">
                {availableCopydeckLines.map((line, idx) => (
                  <button
                    key={idx}
                    onClick={() => setOcrBriefText(line)}
                    className={`flex-shrink-0 w-52 text-left text-sm px-4 py-3 rounded-xl border transition-all ${
                      ocrBriefText === line
                        ? "bg-indigo-50 border-indigo-400 text-indigo-900 shadow-md ring-2 ring-indigo-200/50"
                        : "bg-white border-gray-200 text-gray-700 hover:bg-gray-50 hover:border-gray-300 hover:shadow-sm"
                    }`}
                    title={line}
                  >
                    <span className="line-clamp-4 leading-relaxed">{line}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="px-6 pb-6 pt-2 flex flex-col gap-6 border-t border-gray-100 mt-2">
            <div className="flex items-center justify-between pt-4">
              <button
                onClick={handleRunOcr}
                disabled={isOcrProcessing || (!ocrBoxAcceptance && !ocrBoxEmission)}
                className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-6 py-2 rounded-xl font-semibold transition-colors disabled:opacity-50"
              >
                {isOcrProcessing ? (
                  <ArrowPathIcon className="w-5 h-5 animate-spin" />
                ) : (
                  <DocumentTextIcon className="w-5 h-5" />
                )}
                {isOcrProcessing ? (ocrProgressMessage || "Zczytywanie i analiza...") : "Zczytaj teksty i porównaj"}
              </button>
            </div>
            
            {/* DIFF RESULTS */}
            {(ocrTextAcceptance || ocrTextEmission) && (
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200 flex flex-col gap-4">
                <h4 className="text-sm font-bold text-gray-700 uppercase tracking-wider">Wynik Porównania (Różnice)</h4>
                
                <div className="flex items-center gap-2 text-xs text-gray-500 bg-white border rounded px-3 py-1.5 w-max">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-green-300 block"></span> Dodane</span>
                  <span className="flex items-center gap-1 ml-2"><span className="w-2 h-2 rounded bg-red-300 block"></span> Usunięte</span>
                </div>
                
                {ocrBriefText && ocrTextAcceptance && (
                  <div className="flex flex-col gap-1">
                    <span className="text-xs font-semibold text-gray-500">Brief <span className="mx-1 text-[10px] text-gray-300">vs</span> Acceptance</span>
                    <div className="p-3 bg-white border border-gray-200 rounded font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {diffChars(normalizeTextForDiff(ocrBriefText), normalizeTextForDiff(ocrTextAcceptance)).map((part, i) => (
                        <span key={i} className={part.added ? "bg-green-200 text-green-900 px-0.5 rounded" : part.removed ? "bg-red-200 text-red-900 line-through px-0.5 rounded" : ""}>
                          {part.value}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {ocrBriefText && ocrTextEmission && (
                  <div className="flex flex-col gap-1 mt-2">
                    <span className="text-xs font-semibold text-gray-500">Brief <span className="mx-1 text-[10px] text-gray-300">vs</span> Emission</span>
                    <div className="p-3 bg-white border border-gray-200 rounded font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {diffChars(normalizeTextForDiff(ocrBriefText), normalizeTextForDiff(ocrTextEmission)).map((part, i) => (
                        <span key={i} className={part.added ? "bg-green-200 text-green-900 px-0.5 rounded" : part.removed ? "bg-red-200 text-red-900 line-through px-0.5 rounded" : ""}>
                          {part.value}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                
                {ocrTextAcceptance && ocrTextEmission && !ocrBriefText && (
                  <div className="flex flex-col gap-1 mt-2">
                    <span className="text-xs font-semibold text-gray-500">Acceptance <span className="mx-1 text-[10px] text-gray-300">vs</span> Emission</span>
                    <div className="p-3 bg-white border border-gray-200 rounded font-mono text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {diffChars(normalizeTextForDiff(ocrTextAcceptance), normalizeTextForDiff(ocrTextEmission)).map((part, i) => (
                        <span key={i} className={part.added ? "bg-green-200 text-green-900 px-0.5 rounded" : part.removed ? "bg-red-200 text-red-900 line-through px-0.5 rounded" : ""}>
                          {part.value}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Pending Report Modal (Add Comment) */}
      {pendingReportItem && (
        <div className="fixed inset-0 z-50 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <CameraIcon className="w-5 h-5 text-amber-500" />
                Add shot to Report
              </h2>
              <button 
                onClick={() => setPendingReportItem(null)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6">
              <p className="text-sm text-gray-500 mb-4">
                Screenshot captured at video time: <span className="font-mono font-bold text-gray-700">{pendingReportItem.timecode.toFixed(3)}s</span>.
                Możesz dodać krótki komentarz dla innych testerów lub programistów, that will appear in the PDF file.
              </p>
              
              <textarea
                value={pendingReportItem.comment}
                onChange={(e) => setPendingReportItem({ ...pendingReportItem, comment: e.target.value })}
                placeholder="Np. Tekst legalu jest przesunięty o 5 pikseli w prawo..."
                className="w-full h-24 p-3 border border-gray-200 rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none resize-none text-sm text-gray-700 bg-gray-50"
                autoFocus
              ></textarea>
              
              <div className="flex gap-3 mt-6 justify-end">
                <button
                  onClick={() => setPendingReportItem(null)}
                  className="px-4 py-2 rounded-xl text-sm font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    setReportItems([...reportItems, pendingReportItem]);
                    setPendingReportItem(null);
                  }}
                  className="px-5 py-2 rounded-xl text-sm font-semibold text-white bg-amber-500 hover:bg-amber-600 shadow-sm shadow-amber-500/20 transition-all"
                >
                  Save to report
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Report Cart Modal */}
      {isReportModalOpen && (
        <div className="fixed inset-0 z-50 bg-gray-900/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
              <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                <DocumentTextIcon className="w-5 h-5 text-amber-500" />
                PDF Report Creator ({reportItems.length})
              </h2>
              <button 
                onClick={() => setIsReportModalOpen(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <XMarkIcon className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto flex-1 bg-gray-50/30">
              {reportItems.length === 0 ? (
                <div className="text-center py-12">
                  <CameraIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                  <p className="text-gray-500 font-medium">No screenshots added to report.</p>
                  <p className="text-sm text-gray-400 mt-1">Użyj ikony aparatu na pasku narzędzi podczas pracy.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {reportItems.map((item, index) => (
                    <div key={item.id} className="bg-white border border-gray-200 rounded-xl p-4 flex gap-4 shadow-sm relative group">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-sm">
                        {index + 1}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-gray-800 text-sm">Zrzut z {item.timecode.toFixed(3)}s</span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-600 uppercase">
                            {item.type}
                          </span>
                        </div>
                        {item.comment && (
                          <p className="text-sm text-gray-600 italic break-words">{item.comment}</p>
                        )}
                      </div>
                      <button
                        onClick={() => setReportItems(reportItems.filter(i => i.id !== item.id))}
                        className="opacity-0 group-hover:opacity-100 absolute top-4 right-4 text-red-400 hover:text-red-600 transition-all"
                        title="Remove from report"
                      >
                        <XMarkIcon className="w-5 h-5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="px-6 py-4 border-t border-gray-100 bg-white flex justify-between items-center">
              <button
                onClick={() => setReportItems([])}
                disabled={reportItems.length === 0}
                className="text-sm font-medium text-red-500 hover:text-red-600 disabled:opacity-50 disabled:hover:text-red-500"
              >
                Clear report
              </button>
              
              <button
                onClick={() => {
                  generatePDF();
                  setIsReportModalOpen(false);
                }}
                disabled={reportItems.length === 0}
                className="px-6 py-2 rounded-xl text-sm font-semibold text-white bg-green-500 hover:bg-green-600 shadow-sm shadow-green-500/20 transition-all disabled:opacity-50 disabled:hover:bg-green-500"
              >
                Generate PDF Report
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
