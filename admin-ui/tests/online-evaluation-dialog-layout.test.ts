import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const sourcesPageSource = readFileSync("src/views/sources/SourcesPage.tsx", "utf8");

assert.match(
  sourcesPageSource,
  /<DialogContent className="[^"]*max-h-\[calc\(100dvh-2rem\)\][^"]*overflow-hidden[^"]*sm:max-w-3xl[^"]*">/,
  "the online evaluation dialog should stay within the dynamic viewport instead of growing beyond both edges",
);

assert.match(
  sourcesPageSource,
  /<div className="flex min-h-0 flex-col gap-4">[\s\S]*?<h3 className="text-sm font-medium">Recent checks<\/h3>/,
  "the loaded evaluation body should be allowed to shrink within the bounded dialog",
);

assert.match(
  sourcesPageSource,
  /<div className="flex min-h-0 flex-1 flex-col">\s*<h3 className="text-sm font-medium">Recent checks<\/h3>/,
  "the recent-checks section should own the dialog's remaining height",
);

assert.match(
  sourcesPageSource,
  /<div className="mt-2 min-h-0 flex-1 overflow-y-auto rounded-lg border">/,
  "long evaluation cohorts should scroll inside the recent-checks list while the summary remains visible",
);

console.log("online-evaluation-dialog-layout.test.ts: all assertions passed");
