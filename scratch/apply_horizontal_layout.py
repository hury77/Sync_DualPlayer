#!/usr/bin/env python3
"""
Apply Horizontal Layout feature to SyncDualPlayer.tsx.
Verified against clean baseline (commit 600fbb2, 2026-07-17).

Block boundaries (clean file):
  L2757  PS QA start
  L2838  Copydeck start
  L2862  Video start
  L3408  OCR start
  L3685  Pending Report Modal (OCR ends here)
  L3738  Report Cart Modal
"""

with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

assert 'isHorizontalLayout' not in content, "Already applied – abort"

# ─── 1. Add state ───────────────────────────────────────────────────────────────
content = content.replace(
    "  const [isSinglePlayerMode, setIsSinglePlayerMode] = useState(false);",
    "  const [isSinglePlayerMode, setIsSinglePlayerMode] = useState(false);\n"
    "  const [isHorizontalLayout, setIsHorizontalLayout] = useState(false);"
)

# ─── 2. Max-width ───────────────────────────────────────────────────────────────
content = content.replace(
    "<div className={`${isSinglePlayerMode ? 'max-w-7xl' : 'max-w-[100rem]'} mx-auto px-6 py-6 pb-20 transition-all duration-500`}>",
    "<div className={`${isSinglePlayerMode && !isHorizontalLayout ? 'max-w-7xl' : 'max-w-[100rem]'} mx-auto px-6 py-6 pb-20 transition-all duration-500`}>"
)

# ─── 3. Toggle switch ──────────────────────────────────────────────────────────
OLD_SPAN = "          <span className={`text-sm font-semibold transition-colors cursor-pointer ${isSinglePlayerMode ? 'text-purple-600' : 'text-gray-400'}`} onClick={() => { setIsSinglePlayerMode(true); if (diffMode) deactivateDiffMode(); }}>Single</span>"
NEW_SPAN = """\
          <span className={`text-sm font-semibold transition-colors cursor-pointer ${isSinglePlayerMode ? 'text-purple-600' : 'text-gray-400'}`} onClick={() => { setIsSinglePlayerMode(true); if (diffMode) deactivateDiffMode(); }}>Single</span>

          {isSinglePlayerMode && (
            <div className="flex items-center gap-2 ml-4 border-l border-gray-300 pl-4">
              <span className={`text-xs font-semibold cursor-pointer ${!isHorizontalLayout ? 'text-gray-900' : 'text-gray-400'}`} onClick={() => setIsHorizontalLayout(false)}>Vertical</span>
              <button onClick={() => setIsHorizontalLayout(h => !h)} className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${isHorizontalLayout ? 'bg-indigo-500' : 'bg-gray-300'}`}>
                <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${isHorizontalLayout ? 'translate-x-5' : 'translate-x-1'}`} />
              </button>
              <span className={`text-xs font-semibold cursor-pointer ${isHorizontalLayout ? 'text-indigo-600' : 'text-gray-400'}`} onClick={() => setIsHorizontalLayout(true)}>Horizontal</span>
            </div>
          )}\
"""
content = content.replace(OLD_SPAN, NEW_SPAN)

# ─── 4. Block anchors ──────────────────────────────────────────────────────────
PS_QA_ANCHOR    = "      {/* ── Playstation QA Results Panel ── */}"
COPYDECK_ANCHOR = "      {copydeckData && ("
VIDEO_ANCHOR    = "      {/* Video Panels Area */}"
OCR_ANCHOR      = "      {/* OCR / Compare Copy Panel */}"
PENDING_ANCHOR  = "      {/* Pending Report Modal"  # OCR block ends HERE
REPORT_ANCHOR   = "      {/* Report Cart Modal */}"

for a in [PS_QA_ANCHOR, COPYDECK_ANCHOR, VIDEO_ANCHOR, OCR_ANCHOR, REPORT_ANCHOR]:
    assert content.count(a) == 1, f"Anchor not unique: {a!r}"
assert PENDING_ANCHOR in content

i_psqa    = content.index(PS_QA_ANCHOR)
i_copydeck= content.index(COPYDECK_ANCHOR)
i_video   = content.index(VIDEO_ANCHOR)
i_ocr     = content.index(OCR_ANCHOR)
i_pending = content.index(PENDING_ANCHOR)
i_report  = content.index(REPORT_ANCHOR)

# ─── 5. Slice blocks ───────────────────────────────────────────────────────────
psqa_block     = content[i_psqa    : i_copydeck].rstrip('\n')
copydeck_block = content[i_copydeck: i_video   ].rstrip('\n')
video_block    = content[i_video   : i_ocr     ].rstrip('\n')
ocr_block      = content[i_ocr     : i_pending ].rstrip('\n')  # ← ends before Pending modal
# Everything from Pending modal onward:
after_ocr      = content[i_pending:]

# ─── 6. Patch PS QA: no mb-6 in horizontal mode ────────────────────────────────
psqa_block = psqa_block.replace(
    '        <div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">',
    '        <div className={`bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden${isSinglePlayerMode && isHorizontalLayout ? " h-full" : " mb-6"}`}>'
)

# ─── 7. Patch Copydeck: no mb-6, smaller chips ─────────────────────────────────
copydeck_block = copydeck_block.replace(
    '        <div className="mb-6 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">',
    '        <div className={`bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden${isSinglePlayerMode && isHorizontalLayout ? " h-full" : " mb-6"}`}>'
)
copydeck_block = copydeck_block.replace(
    '              <span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full border border-gray-200">',
    '              <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-[11px] font-semibold rounded-full border border-gray-200">'
)

# ─── 8. Patch Video: remove mb-8 in horizontal mode ────────────────────────────
video_block = video_block.replace(
    "      <div className={`grid grid-cols-1 ${isSinglePlayerMode ? '' : 'lg:grid-cols-2'} gap-6 mb-8`}>",
    "      <div className={`grid grid-cols-1 ${isSinglePlayerMode ? '' : 'lg:grid-cols-2'} gap-6${isSinglePlayerMode && isHorizontalLayout ? '' : ' mb-8'}`}>"
)

# ─── 9. Patch OCR panel ────────────────────────────────────────────────────────
# 9a. Container: flex-col, sticky header support
ocr_block = ocr_block.replace(
    '        <div id="ocr-panel-container" className="mt-8 bg-white rounded-2xl shadow-sm border border-purple-200 overflow-hidden">',
    '        <div id="ocr-panel-container" className={`bg-white rounded-2xl shadow-sm border border-purple-200 flex flex-col${isSinglePlayerMode && isHorizontalLayout ? " max-h-[80vh] overflow-hidden" : " mt-8 overflow-hidden"}`}>'
)

# 9b. After header closing </div>, insert flex-1 overflow-y-auto wrapper
# Header closing pattern (must be unique in ocr_block):
AFTER_HEADER = '          </div>\n          \n          {/* Live Camera Feed Previews */}'
AFTER_HEADER_NEW = '          </div>\n          <div className="flex-1 overflow-y-auto">\n          {/* Live Camera Feed Previews */}'
assert ocr_block.count(AFTER_HEADER) == 1, f"Header close not found in ocr_block"
ocr_block = ocr_block.replace(AFTER_HEADER, AFTER_HEADER_NEW)

# 9c. OCR block ends with:
#           </div>       ← closes "px-6 pb-6 pt-2" div  (indented 10 spaces)
#         </div>         ← closes ocr-panel-container     (indented 8 spaces)
#       )}               ← closes isOcrActive &&          (indented 6 spaces)
# We add </div> to close the flex-1 wrapper before ocr-panel-container closes.
# The exact ending of ocr_block:
assert ocr_block.endswith('        </div>\n      )}'), f"OCR block end unexpected: {ocr_block[-80:]!r}"
ocr_block = ocr_block[:-len('        </div>\n      )}')] + '          </div>\n        </div>\n      )}'

# ─── 10. Assemble ──────────────────────────────────────────────────────────────
NEW_AREA = f"""\
      {{/* ── Main Content Area ── */}}
      <div className={{isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-4" : "flex flex-col gap-6"}}>

        {{/* Row 1: PS QA (narrow left) + Copydeck (wide right) */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-6 items-stretch" : "contents"}}>
          <div className={{isSinglePlayerMode && isHorizontalLayout ? "h-full" : ""}}>
{psqa_block}
          </div>
          <div className={{isSinglePlayerMode && isHorizontalLayout ? "h-full" : ""}}>
{copydeck_block}
          </div>
        </div>

        {{/* Row 2: Video (left, 50%) + OCR (right, 50%, aligned top) */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-2 gap-6 items-start" : "contents"}}>
          <div>
{video_block}
          </div>
          <div>
{ocr_block}
          </div>
        </div>

      </div>
"""

new_content = content[:i_psqa] + NEW_AREA + "\n" + after_ocr

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(new_content)

print("✅ Done!")
