import assert from "node:assert/strict";
import test from "node:test";

import {
  assertAllowedRecipient,
  buildEmailPayload,
  extractLinks,
  parseSimpleMime,
} from "./courts_nz_email_worker.mjs";

test("buildEmailPayload preserves raw MIME and extracts metadata", async () => {
  const raw = [
    "Message-ID: <worker-smoke@example.test>",
    "Subject: Judgment notice",
    "Date: Sun, 14 Jun 2026 06:34:00 GMT",
    "Content-Type: text/plain",
    "",
    "Judgment available at https://www.courtsofnz.govt.nz/cases/example.",
  ].join("\r\n");
  const message = {
    from: "notices@example.test",
    to: "courts-nz-judgments@example.com",
    headers: new Headers({
      "message-id": "<worker-smoke@example.test>",
      "subject": "Judgment notice",
      "date": "Sun, 14 Jun 2026 06:34:00 GMT",
    }),
    raw: new Blob([raw]).stream(),
  };

  const payload = await buildEmailPayload(message);

  assert.equal(payload.message_id, "<worker-smoke@example.test>");
  assert.equal(payload.subject, "Judgment notice");
  assert.equal(payload.text, "Judgment available at https://www.courtsofnz.govt.nz/cases/example.");
  assert.equal(payload.extraction_method, "cloudflare_email_routing_worker");
  assert.deepEqual(payload.links, ["https://www.courtsofnz.govt.nz/cases/example"]);
  assert.equal(Buffer.from(payload.raw_mime_base64, "base64").toString("utf8"), raw);
});

test("assertAllowedRecipient enforces configured recipients", () => {
  assert.doesNotThrow(() =>
    assertAllowedRecipient("COURTS-NZ-JUDGMENTS@example.com", {
      ALLOWED_RECIPIENTS: "courts-nz-judgments@example.com",
    }),
  );
  assert.throws(() =>
    assertAllowedRecipient("other@example.com", {
      ALLOWED_RECIPIENTS: "courts-nz-judgments@example.com",
    }),
  );
  assert.throws(() => assertAllowedRecipient("courts-nz-judgments@example.com", {}));
});

test("extractLinks deduplicates and trims punctuation", () => {
  assert.deepEqual(
    extractLinks("See https://example.test/a. Also https://example.test/a)"),
    ["https://example.test/a"],
  );
});

test("parseSimpleMime handles html-only messages", () => {
  const parsed = parseSimpleMime(
    [
      "Subject: HTML notice",
      "Content-Type: text/html",
      "",
      "<p>Read <a href=\"https://example.test\">the notice</a></p>",
    ].join("\n"),
  );

  assert.equal(parsed.subject, "HTML notice");
  assert.equal(parsed.text, "Read the notice");
  assert.match(parsed.html, /href/);
});
