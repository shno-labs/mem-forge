import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const typesSource = readFileSync("src/api/types.ts", "utf8");
const sourcesPageSource = readFileSync("src/views/sources/SourcesPage.tsx", "utf8");
const sourceRowSource = readFileSync("src/views/sources/SourceRow.tsx", "utf8");

assert.match(
  typesSource,
  /enabled_for_me:\s*boolean/,
  "source responses should expose whether the current user has the source enabled",
);

assert.match(
  sourcesPageSource,
  /\/api\/sources\/\$\{sourceId\}\/subscription/,
  "source subscription changes should use the dedicated per-user subscription endpoint",
);

assert.match(
  sourcesPageSource,
  /invalidateQueries\(\{\s*queryKey:\s*\["memories"\]/,
  "source subscription changes should refresh memory queries for the current user",
);

assert.match(
  sourceRowSource,
  /role="switch"/,
  "source rows should render the per-user source preference as an accessible switch",
);

assert.match(
  sourceRowSource,
  /aria-checked=\{source\.enabled_for_me\}/,
  "the source subscription switch state should come from the source response",
);

assert.match(
  sourceRowSource,
  /Enabled for me/,
  "enabled rows should label that the source participates in the current user's memory context",
);

assert.match(
  sourceRowSource,
  /Disabled for me/,
  "disabled rows should clearly show that the source is muted only for the current user",
);
