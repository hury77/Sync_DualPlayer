import re

with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# Let's find the exact boundaries.
ps_qa_start = content.find("      {isSinglePlayerMode && psQaMetadata && (")
copydeck_start = content.find("      {copydeckData && (")
video_start = content.find("      {/* Video Panels Area */}")
ocr_start = content.find("      {isOcrActive && (")

# But we need to know where they end!
# We can just count braces `{` and `}` to find the end of a JSX expression,
# or we can use the next component's start as a boundary!
# PS QA ends before Copydeck:
ps_qa_code = content[ps_qa_start:copydeck_start]

# Copydeck ends before Video Area:
copydeck_code = content[copydeck_start:video_start]

# Video Area ends before OCR?
# Actually there are other things like Wipe/Diff view between Video Area and OCR.
# Let's check what's between video_start and ocr_start
video_and_wipe_code = content[video_start:ocr_start]

# OCR panel ends... where?
# It ends before System Configuration Modal or Live Camera Feed Previews.
# Wait, Live Camera Feed Previews is INSIDE the OCR Panel (isOcrActive &&)
modal_start = content.find("      {/* ── System Configuration Modal ── */}")
if modal_start == -1:
    modal_start = content.find("      {/* Report Cart Modal */}")

ocr_code = content[ocr_start:modal_start]

# Now we have the pieces!
# We want to re-assemble them.
new_layout = f"""
      {{/* ── Main Content Area ── */}}
      <div className={{isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-1 lg:grid-cols-[1fr_minmax(0,1fr)] gap-8 items-start" : "flex flex-col gap-6"}}>
        
        {{/* Left Column */}}
        <div className="flex flex-col gap-6">
{ps_qa_code}
{video_and_wipe_code}
        </div>

        {{/* Right Column */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6 max-h-[85vh] overflow-y-auto pr-2" : "flex flex-col gap-6"}}>
{copydeck_code}
{ocr_code}
        </div>
      </div>
"""

# Replace the whole section from ps_qa_start to modal_start with new_layout
new_content = content[:ps_qa_start] + new_layout + content[modal_start:]

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(new_content)

print("Reorder successful!")
