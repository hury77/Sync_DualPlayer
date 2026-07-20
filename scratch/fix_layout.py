import re

with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# We need to find the Left Column and Right Column wrappers and replace their classNames
# and add `order-X` to their children.
# Currently they look like:
# <div className="flex flex-col gap-6">  (left column)
# and
# <div className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6 max-h-[85vh] overflow-y-auto pr-2" : "flex flex-col gap-6"}> (right column)

# Let's replace the whole main content area again.
main_area_start = content.find("{/* ── Main Content Area ── */}")
# We need to find where it ends. 
# It ends before System Configuration Modal
modal_start = content.find("      {/* ── System Configuration Modal ── */}")
if modal_start == -1:
    modal_start = content.find("      {/* Report Cart Modal */}")

old_main_area = content[main_area_start:modal_start]

# We will extract the exact blocks from old_main_area.
ps_qa_idx = old_main_area.find("      {isSinglePlayerMode && psQaMetadata && (")
video_idx = old_main_area.find("      {/* Video Panels Area */}")
copydeck_idx = old_main_area.find("      {copydeckData && (")
ocr_idx = old_main_area.find("      {isOcrActive && (")

# PS QA goes up to Video Area
ps_qa_code = old_main_area[ps_qa_idx:video_idx]

# Video Area goes up to the end of left column... wait, where does it end?
# Left column ends before `{/* Right Column */}`
right_col_idx = old_main_area.find("{/* Right Column */}")
video_and_wipe_code = old_main_area[video_idx:right_col_idx]
# clean up trailing `</div>` from the left column wrapper
video_and_wipe_code = video_and_wipe_code.rsplit("        </div>", 1)[0]

# Copydeck goes up to OCR
copydeck_code = old_main_area[copydeck_idx:ocr_idx]

# OCR goes to the end
ocr_code = old_main_area[ocr_idx:]
# clean up trailing `</div>` and `</div>` from right column wrapper and main wrapper
ocr_code = ocr_code.rsplit("        </div>", 1)[0]
ocr_code = ocr_code.rsplit("      </div>", 1)[0]


# Now we reconstruct with the correct order-X wrappers!
new_layout = f"""{{/* ── Main Content Area ── */}}
      <div className={{isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-1 lg:grid-cols-[1fr_minmax(0,1fr)] gap-8 items-start" : "flex flex-col gap-6"}}>
        
        {{/* Left Column */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6" : "contents"}}>
          <div className={{!isHorizontalLayout ? "order-1" : ""}}>
{ps_qa_code}
          </div>
          <div className={{!isHorizontalLayout ? "order-3" : ""}}>
{video_and_wipe_code}
          </div>
        </div>

        {{/* Right Column */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6 max-h-[85vh] overflow-y-auto pr-2" : "contents"}}>
          <div className={{!isHorizontalLayout ? "order-2" : ""}}>
{copydeck_code}
          </div>
          <div className={{!isHorizontalLayout ? "order-5" : ""}}>
{ocr_code}
          </div>
        </div>
      </div>
"""

new_content = content[:main_area_start] + new_layout + content[modal_start:]

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(new_content)

print("Layout fix applied!")
