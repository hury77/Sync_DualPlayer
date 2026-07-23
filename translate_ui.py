with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

translations_str = """
const translations = {
  pl: {
    singlePlayer: "Pojedynczy odtwarzacz",
    dualPlayer: "Dwa odtwarzacze",
    uploadVideo1: "Wgraj Video 1",
    uploadVideo2: "Wgraj Video 2",
    dropVideoHere: "Upuść plik wideo tutaj...",
    selectFileFromDisk: "Wybierz plik z dysku",
    playPause: "Odtwarzaj / Pauza",
    play: "Odtwórz",
    pause: "Pauza",
    rewind: "Przewiń do tyłu",
    forward: "Przewiń do przodu",
    prevFrame: "Poprzednia klatka",
    nextFrame: "Następna klatka",
    zoom: "Skalowanie (Zoom)",
    tools: "Narzędzia",
    heatmapMode: "Tryb Heatmapy",
    sensitivity: "Suwak Czułości",
    low: "Niska",
    medium: "Średnia",
    high: "Wysoka",
    ruler: "Linijka",
    eyedropper: "Kroplomierz",
    copyText: "Kopiuj tekst",
    copied: "Skopiowano!",
    extractedText: "Wyciągnięty Tekst (OCR)",
    saveFrame: "Zapisz klatkę",
    volume: "Głośność",
    video1: "Video 1",
    video2: "Video 2",
    pixels: "Piksele:",
    audioDiff: "Różnice audio",
    playerMode: "Tryb odtwarzacza",
    videoLoadingError: "Błąd ładowania wideo",
    changeToDarkBg: "Zmień na ciemne tło wideo",
    changeToLightBg: "Zmień na jasne tło wideo",
    uploadLocBrief: "Wgraj LOC Brief (.xlsx)",
    chooseRowFromExcel: "Wybierz wiersz z pliku Excel (Copydeck):",
    comparisonResult: "Wynik Porównania (Różnice)",
    turnOffEyedropper: "Wyłącz próbnik koloru (Kroplomierz)",
    turnOnEyedropper: "Włącz próbnik koloru (Kroplomierz, aktywny na pauzie)",
    turnOffRuler: "Wyłącz miarkę (Linijka)",
    turnOnRuler: "Włącz miarkę pikseli (Linijka, aktywna na pauzie)",
    audioDiffAlert: "Rozjazd Audio!",
    videoPreviewInsp: "Video Preview (Inspection)"
  },
  en: {
    singlePlayer: "Single Player",
    dualPlayer: "Dual Player",
    uploadVideo1: "Upload Video 1",
    uploadVideo2: "Upload Video 2",
    dropVideoHere: "Drop video file here...",
    selectFileFromDisk: "Select file from disk",
    playPause: "Play / Pause",
    play: "Play",
    pause: "Pause",
    rewind: "Rewind",
    forward: "Fast Forward",
    prevFrame: "Previous Frame",
    nextFrame: "Next Frame",
    zoom: "Zoom",
    tools: "Tools",
    heatmapMode: "Heatmap Mode",
    sensitivity: "Sensitivity Slider",
    low: "Low",
    medium: "Medium",
    high: "High",
    ruler: "Ruler",
    eyedropper: "Eyedropper",
    copyText: "Copy text",
    copied: "Copied!",
    extractedText: "Extracted Text (OCR)",
    saveFrame: "Save frame",
    volume: "Volume",
    video1: "Video 1",
    video2: "Video 2",
    pixels: "Pixels:",
    audioDiff: "Audio Diff",
    playerMode: "Player Mode",
    videoLoadingError: "Video Loading Error",
    changeToDarkBg: "Change to dark video background",
    changeToLightBg: "Change to light video background",
    uploadLocBrief: "Upload LOC Brief (.xlsx)",
    chooseRowFromExcel: "Choose row from Excel file (Copydeck):",
    comparisonResult: "Comparison Result (Differences)",
    turnOffEyedropper: "Turn off eyedropper",
    turnOnEyedropper: "Turn on eyedropper (active on pause)",
    turnOffRuler: "Turn off ruler",
    turnOnRuler: "Turn on pixel ruler (active on pause)",
    audioDiffAlert: "Audio Diff!",
    videoPreviewInsp: "Video Preview (Inspection)"
  }
};
"""

content = content.replace("export default function SyncDualPlayer() {", translations_str + "\nexport default function SyncDualPlayer() {")

state_str = """
  const [language, setLanguage] = useState<'pl' | 'en'>('pl');
  const t = (key: keyof typeof translations.pl) => translations[language][key];
"""
content = content.replace("export default function SyncDualPlayer() {\n", "export default function SyncDualPlayer() {\n" + state_str)

switcher_str = """
        <div className="flex items-center gap-2">
          <button 
            onClick={() => setLanguage('pl')} 
            className={`px-2 py-1 text-xs font-bold rounded-md ${language === 'pl' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
          >
            PL
          </button>
          <button 
            onClick={() => setLanguage('en')} 
            className={`px-2 py-1 text-xs font-bold rounded-md ${language === 'en' ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
          >
            EN
          </button>
        </div>
"""
content = content.replace('<div className="flex items-center gap-4">', '<div className="flex items-center gap-4">\n' + switcher_str)

replacements = {
    '>Pojedynczy odtwarzacz<': '>{t("singlePlayer")}<',
    '>Dwa odtwarzacze<': '>{t("dualPlayer")}<',
    '>Wgraj Video 1<': '>{t("uploadVideo1")}<',
    '>Wgraj Video 2<': '>{t("uploadVideo2")}<',
    '>Upuść plik wideo tutaj...<': '>{t("dropVideoHere")}<',
    '>Wybierz plik z dysku<': '>{t("selectFileFromDisk")}<',
    'title="Odtwarzaj / Pauza"': 'title={t("playPause")}',
    'title="Odtwórz"': 'title={t("play")}',
    'title="Pauza"': 'title={t("pause")}',
    'title="Przewiń do tyłu"': 'title={t("rewind")}',
    'title="Przewiń do przodu"': 'title={t("forward")}',
    'title="Poprzednia klatka"': 'title={t("prevFrame")}',
    'title="Następna klatka"': 'title={t("nextFrame")}',
    '>Skalowanie (Zoom)<': '>{t("zoom")}<',
    '>Narzędzia<': '>{t("tools")}<',
    '>Tryb Heatmapy (Diff)<': '>{t("heatmapMode")}<',
    '>Suwak Czułości (Heatmapa)<': '>{t("sensitivity")}<',
    '>Niska<': '>{t("low")}<',
    '>Średnia<': '>{t("medium")}<',
    '>Wysoka<': '>{t("high")}<',
    '>Linijka<': '>{t("ruler")}<',
    '>Kroplomierz<': '>{t("eyedropper")}<',
    '>Kopiuj tekst<': '>{t("copyText")}<',
    '>Skopiowano!<': '>{t("copied")}<',
    '>Wyciągnięty Tekst (OCR)<': '>{t("extractedText")}<',
    'title="Zapisz klatkę"': 'title={t("saveFrame")}',
    'title="Głośność"': 'title={t("volume")}',
    '>Piksele:<': '>{t("pixels")}<',
    '>Różnice audio<': '>{t("audioDiff")}<',
    '>Tryb odtwarzacza<': '>{t("playerMode")}<',
    '>Video Loading Error<': '>{t("videoLoadingError")}<',
    'title={isVideoBgLight ? "Zmień na ciemne tło wideo" : "Zmień na jasne tło wideo"}': 'title={isVideoBgLight ? t("changeToDarkBg") : t("changeToLightBg")}',
    'title="Wgraj LOC Brief (.xlsx)"': 'title={t("uploadLocBrief")}',
    '>Wybierz wiersz z pliku Excel (Copydeck):<': '>{t("chooseRowFromExcel")}<',
    '>Wynik Porównania (Różnice)<': '>{t("comparisonResult")}<',
    'title={isEyedropperActive ? "Wyłącz próbnik koloru (Kroplomierz)" : "Włącz próbnik koloru (Kroplomierz, aktywny na pauzie)"}': 'title={isEyedropperActive ? t("turnOffEyedropper") : t("turnOnEyedropper")}',
    'title={isRulerActive ? "Wyłącz miarkę (Linijka)" : "Włącz miarkę pikseli (Linijka, aktywna na pauzie)"}': 'title={isRulerActive ? t("turnOffRuler") : t("turnOnRuler")}',
    'value={isSinglePlayerMode ? \'Video Preview (Inspection)\' : acceptanceCustomName}': 'value={isSinglePlayerMode ? t("videoPreviewInsp") : acceptanceCustomName}'
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(content)
