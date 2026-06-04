import assert from "node:assert/strict";

import { buildFailureDetails } from "../src/components/admin/syncFailureDetails.js";

const embeddingDetails = buildFailureDetails({
  failed_docs: [
    {
      title: "Payroll_run_request_stuck",
      error: "Embedding provider unreachable: [Errno 111] Connection refused",
    },
  ],
});

assert.equal(embeddingDetails?.groups[0]?.label, "Embedding provider unreachable");
assert.equal(
  embeddingDetails?.groups[0]?.help,
  "MemForge could not reach the configured embedding provider. Check the provider endpoint, network access, and service status, then retry the sync.",
);

const llmDetails = buildFailureDetails({
  failed_docs: [
    {
      title: "Payroll_run_not_getting_triggered",
      error: "litellm.InternalServerError: AnthropicException - Cannot connect to host provider.example:443",
    },
  ],
});

assert.equal(llmDetails?.groups[0]?.label, "LLM provider unreachable");
assert.equal(
  llmDetails?.groups[0]?.help,
  "MemForge could not reach the configured LLM provider. Check the provider endpoint, network access, and service status, then retry the sync.",
);
