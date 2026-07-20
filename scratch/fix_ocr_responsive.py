with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# 1. Fix OCR Header
old_header = """          <div className="px-6 py-4 border-b border-purple-100 bg-purple-50/50 flex justify-between items-center">
            <h3 className="font-semibold text-purple-900 flex items-center gap-2">
              <DocumentTextIcon className="w-5 h-5" /> Compare Copy (OCR)
            </h3>
            <div className="flex items-center gap-4">"""

new_header = """          <div className="px-6 py-4 border-b border-purple-100 bg-purple-50/50 flex flex-wrap justify-between items-center gap-4">
            <h3 className="font-semibold text-purple-900 flex items-center gap-2 min-w-max">
              <DocumentTextIcon className="w-5 h-5" /> Compare Copy (OCR)
            </h3>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">"""

content = content.replace(old_header, new_header)

# 2. Add whitespace-nowrap to "Czułość kontrastu:"
content = content.replace(
    '<span className="text-xs text-purple-700 font-semibold">Czułość kontrastu:</span>',
    '<span className="text-xs text-purple-700 font-semibold whitespace-nowrap">Czułość kontrastu:</span>'
)

# 3. Add whitespace-nowrap to Jasny tekst label
old_label = '<label className="flex items-center gap-1.5 text-xs text-purple-800 cursor-pointer hover:bg-purple-100 px-2 py-1 rounded transition-colors">'
new_label = '<label className="flex items-center gap-1.5 text-xs text-purple-800 cursor-pointer hover:bg-purple-100 px-2 py-1 rounded transition-colors whitespace-nowrap">'
content = content.replace(old_label, new_label)

# 4. Fix grid-cols-3
old_grid = '<div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">'
new_grid = '<div className={`p-6 grid grid-cols-1 ${isSinglePlayerMode && isHorizontalLayout ? "xl:grid-cols-1" : "md:grid-cols-3"} gap-6`}>'
content = content.replace(old_grid, new_grid)

# 5. Fix text overlap in the headers of those 3 columns
old_col_headers = [
    '<label className="text-sm font-semibold text-gray-700">Skopiowany Brief',
    '<label className="text-sm font-semibold text-green-700">Text from Acceptance',
    '<label className="text-sm font-semibold text-red-700">Text from Emission'
]

for old in old_col_headers:
    new_h = old.replace('text-sm', 'text-sm whitespace-normal break-words')
    content = content.replace(old, new_h)

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(content)

print("Responsive fixes applied!")
