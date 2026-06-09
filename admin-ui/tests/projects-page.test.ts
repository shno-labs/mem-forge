import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const projectsSource = readFileSync("src/views/projects/ProjectsPage.tsx", "utf8");
const projectDetailSource = readFileSync(
  "src/views/projects/ProjectDetailPage.tsx",
  "utf8",
);

assert.match(
  projectsSource,
  /Sources can stay unmapped until you assign them\./,
  "the Projects page should describe user-created project labels without exposing system buckets",
);

assert.doesNotMatch(
  projectsSource,
  /System buckets|RESERVED_PROJECT_KEYS|SHARED|UNSORTED/,
  "the Projects page should not render reserved buckets as manageable projects",
);

assert.doesNotMatch(
  projectsSource,
  /unsorted bucket/i,
  "project deletion feedback should use unmapped wording, not internal unsorted wording",
);

assert.doesNotMatch(
  projectDetailSource,
  /unsorted bucket/i,
  "project detail deletion confirmation should use unmapped wording, not internal unsorted wording",
);

console.log("projects-page.test.ts: all assertions passed");
