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

# 4. Wrap layout blocks.
ps_qa_idx = content.find("      {isSinglePlayerMode && psQaMetadata && (")
copydeck_idx = content.find("      {copydeckData && (")
video_idx = content.find("      {/* Video Panels Area */}")
ocr_idx = content.find("      {isOcrActive && (")
modal_idx = content.find("      {/* Report Cart Modal */}")

ps_qa_code = content[ps_qa_idx:copydeck_idx]
copydeck_code = content[copydeck_idx:video_idx]
video_wipe_code = content[video_idx:ocr_idx]
ocr_code = content[ocr_idx:modal_idx]

# Construct the new main area!
new_layout = f"""
      {{/* ── Main Content Area ── */}}
      <div className={{isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-1 lg:grid-cols-[1fr_minmax(0,1fr)] gap-8 items-start" : "flex flex-col gap-6"}}>
        
        {{/* Left Column */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6" : "contents"}}>
          <div className={{!isHorizontalLayout ? "order-1 w-full" : "w-full"}}>
{ps_qa_code.rstrip()}
          </div>
          <div className={{!isHorizontalLayout ? "order-3 w-full" : "w-full"}}>
{video_wipe_code.rstrip()}
          </div>
        </div>

        {{/* Right Column */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6 max-h-[85vh] overflow-y-auto pr-2" : "contents"}}>
          <div className={{!isHorizontalLayout ? "order-2 w-full" : "w-full"}}>
{copydeck_code.rstrip()}
          </div>
          <div className={{!isHorizontalLayout ? "order-4 w-full" : "w-full"}}>
{ocr_code.rstrip()}
          </div>
        </div>
      </div>
"""

# Replace exactly from ps_qa_idx to modal_idx
new_content = content[:ps_qa_idx] + new_layout + "\n" + content[modal_idx:]

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(new_content)

print("Layout rewritten successfully!")
