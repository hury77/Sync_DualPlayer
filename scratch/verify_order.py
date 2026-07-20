with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

print("PS QA:", content.find("{isSinglePlayerMode && psQaMetadata && ("))
print("Copydeck:", content.find("{copydeckData && ("))
print("Video:", content.find("{/* Video Panels Area */}"))
print("Wipe:", content.find("{/* Wipe / Diff View (Overlay) */}"))
print("OCR:", content.find("{/* ── OCR Results Panel ── */}")) # assuming this comment doesn't exist. Let's find "Wyniki i Roznice OCR"
print("OCR2:", content.find("Wyniki i Roznice OCR"))
print("Live Camera:", content.find("{/* Live Camera Feed Previews */}"))
print("Report Modal:", content.find("{/* Report Cart Modal */}"))
