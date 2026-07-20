import re

with open('frontend/src/components/SyncDualPlayer.tsx', 'r') as f:
    content = f.read()

# 1. Update the Main Content Area Grid
# from: <div className={isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-1 lg:grid-cols-[1fr_minmax(0,1fr)] gap-8 items-start" : "flex flex-col gap-6"}>
# to: <div className={isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-[minmax(0,5fr)_minmax(0,6fr)] gap-6 items-start" : "flex flex-col gap-6"}>
content = content.replace(
    'className={isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-1 lg:grid-cols-[1fr_minmax(0,1fr)] gap-8 items-start" : "flex flex-col gap-6"}',
    'className={isSinglePlayerMode && isHorizontalLayout ? "grid grid-cols-[minmax(0,5fr)_minmax(0,7fr)] gap-8 items-start" : "flex flex-col gap-6"}'
)

# 2. Update Left Column wrapper
# from: <div className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6" : "contents"}>
# to: <div className="contents">
content = content.replace(
    '<div className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6" : "contents"}>',
    '<div className="contents">'
)

# 3. Update Right Column wrapper
# from: <div className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6 max-h-[85vh] overflow-y-auto pr-2" : "contents"}>
# to: <div className="contents">
content = content.replace(
    '<div className={isSinglePlayerMode && isHorizontalLayout ? "flex flex-col gap-6 max-h-[85vh] overflow-y-auto pr-2" : "contents"}>',
    '<div className="contents">'
)

# 4. Update the order/grid classes for the 4 panels

# PS QA
content = content.replace(
    '<div className={!isHorizontalLayout ? "order-1 w-full" : "w-full"}>',
    '<div className={!isHorizontalLayout ? "order-1 w-full" : "col-start-1 row-start-1 h-full w-full"}>'
)

# Video and Wipe (this wrapper is around Video Area)
content = content.replace(
    '<div className={!isHorizontalLayout ? "order-3 w-full" : "w-full"}>',
    '<div className={!isHorizontalLayout ? "order-3 w-full" : "col-start-1 row-start-2 w-full"}>'
)

# Copydeck
content = content.replace(
    '<div className={!isHorizontalLayout ? "order-2 w-full" : "w-full"}>',
    '<div className={!isHorizontalLayout ? "order-2 w-full" : "col-start-2 row-start-1 h-full w-full"}>'
)

# OCR
content = content.replace(
    '<div className={!isHorizontalLayout ? "order-4 w-full" : "w-full"}>',
    '<div className={!isHorizontalLayout ? "order-4 w-full" : "col-start-2 row-start-2 max-h-[85vh] overflow-y-auto pr-2 w-full"}>'
)


# 5. Make Copydeck languages font smaller to fit better
# from: <span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full border border-gray-200">
# to: <span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-[11px] font-semibold rounded-full border border-gray-200">
content = content.replace(
    '<span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-semibold rounded-full border border-gray-200">',
    '<span key={idx} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-[11px] font-semibold rounded-full border border-gray-200">'
)

with open('frontend/src/components/SyncDualPlayer.tsx', 'w') as f:
    f.write(content)

print("Alignment fixed!")
