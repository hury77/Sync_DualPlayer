import re

with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# 1. Add state
content = content.replace(
    "  const [isSinglePlayerMode, setIsSinglePlayerMode] = useState(false);",
    "  const [isSinglePlayerMode, setIsSinglePlayerMode] = useState(false);\n  const [isHorizontalLayout, setIsHorizontalLayout] = useState(false);"
)

# 2. Adjust max width
content = content.replace(
    "<div className={`${isSinglePlayerMode ? 'max-w-7xl' : 'max-w-[100rem]'} mx-auto px-6 py-6 pb-20 transition-all duration-500`}>",
    "<div className={`${isSinglePlayerMode && !isHorizontalLayout ? 'max-w-7xl' : 'max-w-[100rem]'} mx-auto px-6 py-6 pb-20 transition-all duration-500`}>"
)

# 3. Add toggle UI
old_toggle = "          <span className={`text-sm font-semibold transition-colors cursor-pointer ${isSinglePlayerMode ? 'text-purple-600' : 'text-gray-400'}`} onClick={() => { setIsSinglePlayerMode(true); if (diffMode) deactivateDiffMode(); }}>Single</span>"

new_toggle = """          <span className={`text-sm font-semibold transition-colors cursor-pointer ${isSinglePlayerMode ? 'text-purple-600' : 'text-gray-400'}`} onClick={() => { setIsSinglePlayerMode(true); if (diffMode) deactivateDiffMode(); }}>Single</span>
          
          {isSinglePlayerMode && (
            <div className="flex items-center gap-2 ml-4 border-l border-gray-300 pl-4">
              <span className={`text-xs font-semibold cursor-pointer ${!isHorizontalLayout ? 'text-gray-900' : 'text-gray-400'}`} onClick={() => setIsHorizontalLayout(false)}>Vertical</span>
              <button
                onClick={() => setIsHorizontalLayout(!isHorizontalLayout)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                  isHorizontalLayout ? 'bg-indigo-500' : 'bg-gray-300'
                }`}
              >
                <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                  isHorizontalLayout ? 'translate-x-5' : 'translate-x-1'
                }`} />
              </button>
              <span className={`text-xs font-semibold cursor-pointer ${isHorizontalLayout ? 'text-indigo-600' : 'text-gray-400'}`} onClick={() => setIsHorizontalLayout(true)}>Horizontal</span>
            </div>
          )}"""
content = content.replace(old_toggle, new_toggle)

# 4. We will use CSS classes on the existing blocks instead of moving JSX around.
# The `max-w-7xl` div contains all the panels as direct children.
# We can make the max-w-7xl div a CSS Grid or Flex container if horizontal layout is active.
# Actually, the direct children of the `max-w-7xl` container are:
# - Header
# - Top Toolbar
# - PS QA Results Panel
# - Copydeck Results Panel
# - Video Panels Area
# - Wipe / Diff View
# - OCR Panel

# Wait! It's much easier to just add wrapper divs by splitting the string.

parts = content.split("      {isSinglePlayerMode && psQaMetadata && (")
if len(parts) == 2:
    before = parts[0]
    rest1 = "      {isSinglePlayerMode && psQaMetadata && (" + parts[1]
    
    parts2 = rest1.split("      {copydeckData && (")
    if len(parts2) == 2:
        psqa = parts2[0]
        rest2 = "      {copydeckData && (" + parts2[1]
        
        parts3 = rest2.split("      {/* Video Panels Area */}")
        if len(parts3) == 2:
            copydeck = parts3[0]
            rest3 = "      {/* Video Panels Area */}" + parts3[1]
            
            parts4 = rest3.split("      {/* ── System Configuration Modal ── */}")
            if len(parts4) == 2:
                video_and_ocr = parts4[0]
                system_modal = "      {/* ── System Configuration Modal ── */}" + parts4[1]
                
                # We need to split video_and_ocr into video and ocr.
                # Video area + Wipe view ends where OCR starts.
                # OCR starts around line 3400.
                parts5 = video_and_ocr.split("      {/* ── OCR Results Panel ── */}")
                # Let's search for OCR comment
                ocr_idx = video_and_ocr.find("      <div className=\"bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-sm mt-8\">")
                if ocr_idx == -1:
                    # try another one
                    ocr_idx = video_and_ocr.find("      <div className=\"mt-8\">")
                if ocr_idx == -1:
                    ocr_idx = video_and_ocr.find("      <div className=\"mb-6")
                
                # I'll just use a safer approach: wrap the whole section with a class that sets display: flex; flex-direction: column;
                # And when horizontal layout is active: grid, grid-cols-2.
                # Since we don't know the exact indices, let's just use CSS `order` by adding classes to the children!
                pass

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(content)
