with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# Fix the column headers to allow wrapping/stacking
content = content.replace(
    '<div className="flex items-center justify-between">\n                <label className="text-sm whitespace-normal break-words font-semibold text-gray-700">Skopiowany Brief (wklej tutaj)</label>',
    '<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">\n                <label className="text-sm whitespace-normal break-words font-semibold text-gray-700">Skopiowany Brief</label>'
)

content = content.replace(
    '<div className="flex items-center justify-between">\n                <label className="text-sm whitespace-normal break-words font-semibold text-green-700">Text from Acceptance video</label>',
    '<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">\n                <label className="text-sm whitespace-normal break-words font-semibold text-green-700">Text from Acceptance</label>'
)

content = content.replace(
    '<div className="flex items-center justify-between">\n                <label className="text-sm whitespace-normal break-words font-semibold text-red-700">Text from Emission video</label>',
    '<div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">\n                <label className="text-sm whitespace-normal break-words font-semibold text-red-700">Text from Emission</label>'
)

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(content)

print("Headers fixed!")
