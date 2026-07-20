with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# 1. Update the Main Content Area wrapper
# From: <div className={isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-8 items-stretch" : "flex flex-col gap-6"}>
# To: <div className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-8" : "flex flex-col gap-6"}>
content = content.replace(
    'className={isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-8 items-stretch" : "flex flex-col gap-6"}',
    'className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-8" : "flex flex-col gap-6"}'
)

# 2. We need to introduce the Row 1 and Row 2 wrappers, replacing the Left/Right column wrappers.
# Currently we have:
#         {/* Left Column */}
#         <div className="contents">
#           <div className={!isHorizontalLayout ? "order-1 w-full" : "col-start-1 row-start-1 h-full w-full"}>
#              [PS QA]
#           </div>
#           <div className={!isHorizontalLayout ? "order-3 w-full" : "col-start-1 row-start-2 w-full"}>
#              [VIDEO]
#           </div>
#         </div>
# 
#         {/* Right Column */}
#         <div className="contents">
#           <div className={!isHorizontalLayout ? "order-2 w-full" : "col-start-2 row-start-1 h-full w-full"}>
#              [COPYDECK]
#           </div>
#           <div className={!isHorizontalLayout ? "order-4 w-full" : "col-start-2 row-start-2 max-h-[85vh] overflow-y-auto pr-2 w-full"}>
#              [OCR]
#           </div>
#         </div>

# We need to extract the 4 blocks.
ps_qa_idx = content.find('      {isSinglePlayerMode && psQaMetadata && (')
copydeck_idx = content.find('      {copydeckData && (')
video_idx = content.find('      {/* Video Panels Area */}')
ocr_idx = content.find('      {isOcrActive && (')
modal_idx = content.find('      {/* Report Cart Modal */}')

# Actually, the blocks are wrapped in those divs. We need to extract the exact text of the blocks.
ps_qa_code = content[ps_qa_idx:content.find('          </div>\n          <div className={!isHorizontalLayout ? "order-3 w-full"', ps_qa_idx)]
video_code = content[video_idx:content.find('          </div>\n        </div>\n\n        {/* Right Column */}', video_idx)]
copydeck_code = content[copydeck_idx:content.find('          </div>\n          <div className={!isHorizontalLayout ? "order-4 w-full"', copydeck_idx)]
ocr_code = content[ocr_idx:content.find('          </div>\n        </div>\n      </div>\n\n      {/* Report Cart Modal */}', ocr_idx)]

# Construct the new HTML
new_layout = f"""
        {{/* Row 1: PS QA and Copydeck */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-8 items-stretch" : "contents"}}>
          <div className={{!isHorizontalLayout ? "order-1 w-full" : "h-full w-full"}}>
{ps_qa_code.rstrip()}
          </div>
          <div className={{!isHorizontalLayout ? "order-2 w-full" : "h-full w-full"}}>
{copydeck_code.rstrip()}
          </div>
        </div>

        {{/* Row 2: Video and OCR */}}
        <div className={{isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-2 gap-8 items-start" : "contents"}}>
          <div className={{!isHorizontalLayout ? "order-3 w-full" : "w-full"}}>
{video_code.rstrip()}
          </div>
          <div className={{!isHorizontalLayout ? "order-4 w-full" : "max-h-[85vh] overflow-y-auto pr-2 w-full"}}>
{ocr_code.rstrip()}
          </div>
        </div>
"""

# Find the bounds to replace
# Start right after: <div className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-8" : "flex flex-col gap-6"}>
start_repl = content.find('      {/* Left Column */}')
end_repl = content.find('      {/* Report Cart Modal */}')

# Note: We need to leave the closing `</div>` of the Main Content Area.
# So end_repl should be before `      </div>\n\n      {/* Report Cart Modal */}`
# The original ended with `          </div>\n        </div>\n      </div>\n\n      {/* Report Cart Modal */}`
# We will just reconstruct up to `      </div>\n\n      {/* Report Cart Modal */}`
end_repl = content.find('      </div>\n\n      {/* Report Cart Modal */}')

new_content = content[:start_repl] + new_layout.strip() + "\n" + content[end_repl:]

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(new_content)

print("Split Grid applied!")
