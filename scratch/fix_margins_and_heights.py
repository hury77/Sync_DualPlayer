with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# 1. PS QA & Copydeck both use: <div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
# We will replace both occurrences to dynamically use h-full and remove mb-6 in horizontal mode.
content = content.replace(
    '<div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">',
    '<div className={`bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden flex flex-col ${isSinglePlayerMode && isHorizontalLayout ? "h-full" : "mb-6"}`}>'
)

# 2. OCR Panel has: <div id="ocr-panel-container" className="mt-8 bg-white rounded-2xl shadow-sm border border-purple-200 overflow-hidden">
# We must remove `mt-8` in horizontal mode, because the grid gap already provides spacing, and it breaks vertical alignment with Video.
content = content.replace(
    '<div id="ocr-panel-container" className="mt-8 bg-white rounded-2xl shadow-sm border border-purple-200 overflow-hidden">',
    '<div id="ocr-panel-container" className={`bg-white rounded-2xl shadow-sm border border-purple-200 overflow-hidden flex flex-col ${isSinglePlayerMode && isHorizontalLayout ? "h-full" : "mt-8"}`}>'
)

# 3. Grid wrapper has items-start. Wait! If grid has items-start, the row won't force items to stretch if they don't have implicit stretch.
# We already added h-full to the inner wrapper, but the outer wrapper (col-start-1 row-start-1 w-full) must NOT have items-start on the main grid if we want them to stretch natively.
# Let's change `gap-8 items-start` to `gap-8 items-stretch` on the main grid.
content = content.replace(
    'gap-8 items-start',
    'gap-8 items-stretch'
)

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(content)

print("Margins and heights fixed!")
