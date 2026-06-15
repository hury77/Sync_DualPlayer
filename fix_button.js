const fs = require('fs');
let content = fs.readFileSync('frontend/src/components/SyncDualPlayer.tsx', 'utf8');

const oldClasses = \`className={\\\`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed \\\${\`;

const newClasses = \`className={\\\`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold shadow-sm transition-all disabled:opacity-100 disabled:bg-gray-200 disabled:text-gray-400 disabled:shadow-none disabled:cursor-not-allowed \\\${\`;

content = content.replace(oldClasses, newClasses); // Replaces first occurrence (Diff Mode button if it matches, wait, let's just target QA Analysis specifically)

fs.writeFileSync('frontend/src/components/SyncDualPlayer.tsx', content);
