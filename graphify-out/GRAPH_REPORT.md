# Graph Report - .  (2026-08-04)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 245 nodes · 229 edges · 62 communities (55 shown, 7 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a340d54e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- main.py
- devDependencies
- compilerOptions
- compilerOptions
- SyncDualPlayer.tsx
- dependencies
- package.json
- AppDelegate
- test-jspdf.cjs
- fix_button.js
- diffWorker.ts
- tsconfig.json
- test_match_exact.py
- build_dmg.sh
- run_and_test.sh
- start.sh

## God Nodes (most connected - your core abstractions)
1. `compilerOptions` - 17 edges
2. `compilerOptions` - 16 edges
3. `analyze_elements()` - 10 edges
4. `get_cached_brief_data()` - 7 edges
5. `upload_file()` - 6 edges
6. `ParserError` - 6 edges
7. `transcode_to_mp4()` - 5 edges
8. `match_brief_icon_to_db()` - 5 edges
9. `parse_filename()` - 5 edges
10. `get_requirements_from_brief()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `AnalyzeFrameRequest` --uses--> `ParserError`  [INFERRED]
  backend/main.py → backend/parsers.py
- `get_cached_brief_data()` --calls--> `extract_rating_icon_from_brief()`  [EXTRACTED]
  backend/main.py → backend/parsers.py
- `get_cached_brief_data()` --calls--> `get_requirements_from_brief()`  [EXTRACTED]
  backend/main.py → backend/parsers.py
- `analyze_elements()` --calls--> `parse_filename()`  [EXTRACTED]
  backend/main.py → backend/parsers.py

## Import Cycles
- None detected.

## Communities (62 total, 7 thin omitted)

### Community 0 - "main.py"
Cohesion: 0.10
Nodes (36): analyze_elements(), AnalyzeFrameRequest, clear_qa_assets(), debug_assets(), delete_file(), get_base64_from_path(), get_cached_brief_data(), get_cached_image() (+28 more)

### Community 1 - "devDependencies"
Cohesion: 0.06
Nodes (33): autoprefixer, eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, devDependencies, autoprefixer, eslint (+25 more)

### Community 2 - "compilerOptions"
Cohesion: 0.09
Nodes (22): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection, moduleResolution (+14 more)

### Community 3 - "compilerOptions"
Cohesion: 0.10
Nodes (20): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+12 more)

### Community 4 - "SyncDualPlayer.tsx"
Cohesion: 0.14
Nodes (13): App(), getBoundedDimensions(), LANGUAGE_TO_TESSERACT, normalizeTextForDiff(), IMPORTANT: Do NOT call video.load() here — it resets the element to HAVE_NOTHING, ReportItem, RulerLine, ShapeType (+5 more)

### Community 5 - "dependencies"
Cohesion: 0.12
Nodes (17): diff, dependencies, diff, @heroicons/react, html2canvas, jspdf, react, react-dom (+9 more)

### Community 6 - "package.json"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, dev, lint, preview, type (+1 more)

### Community 7 - "AppDelegate"
Cohesion: 0.33
Nodes (5): NSApplicationDelegate, NSObject, AppDelegate, -applicationDidFinishLaunching, -applicationShouldTerminate

### Community 8 - "test-jspdf.cjs"
Cohesion: 0.40
Nodes (4): base64Content, fs, { jsPDF }, match

## Knowledge Gaps
- **87 isolated node(s):** `build_dmg.sh script`, `fs`, `content`, `name`, `private` (+82 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **7 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `devDependencies` connect `devDependencies` to `package.json`?**
  _High betweenness centrality (0.045) - this node is a cross-community bridge._
- **Why does `dependencies` connect `dependencies` to `package.json`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **What connects `build_dmg.sh script`, `fs`, `content` to the rest of the system?**
  _87 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `main.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10121457489878542 - nodes in this community are weakly interconnected._
- **Should `devDependencies` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.08695652173913043 - nodes in this community are weakly interconnected._
- **Should `compilerOptions` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._