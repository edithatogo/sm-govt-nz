const DEFAULT_GITHUB_REPO = "edithatogo/sm-govt-nz";
const DISPATCH_EVENT_TYPE = "courts_nz_email_received";

export default {
  async email(message, env) {
    try {
      assertAllowedRecipient(message.to, env);
      const payload = await buildEmailPayload(message);
      await dispatchToGitHub(payload, env);
    } catch (error) {
      console.error("Courts of NZ email archive dispatch failed", error);
      message.setReject("Unable to archive message");
    }
  },
};

export async function buildEmailPayload(message) {
  const rawBytes = await readRawBytes(message.raw);
  const rawText = decodeUtf8(rawBytes);
  const parsed = parseSimpleMime(rawText);
  const subject = header(message.headers, "subject") || parsed.subject;
  const text = parsed.text.trim();
  const html = parsed.html.trim();
  const bodyForLinks = [text, html].filter(Boolean).join("\n");

  return {
    message_id: header(message.headers, "message-id") || parsed.messageId,
    from: message.from || header(message.headers, "from"),
    to: message.to || header(message.headers, "to"),
    subject,
    text,
    html,
    received_at: normalizeDate(header(message.headers, "date") || parsed.date),
    links: extractLinks(bodyForLinks),
    raw_mime_base64: base64Encode(rawBytes),
  };
}

export async function dispatchToGitHub(payload, env) {
  const token = env.GITHUB_TOKEN;
  if (!token) {
    throw new Error("Missing GITHUB_TOKEN Worker secret");
  }
  const repo = env.GITHUB_REPO || DEFAULT_GITHUB_REPO;
  const response = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
    method: "POST",
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      "User-Agent": "sm-govt-nz-cloudflare-email-worker",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    body: JSON.stringify({
      event_type: DISPATCH_EVENT_TYPE,
      client_payload: payload,
    }),
  });
  if (!response.ok) {
    throw new Error(`GitHub dispatch failed: ${response.status} ${await response.text()}`);
  }
}

export function assertAllowedRecipient(recipient, env) {
  const allowed = splitList(env.ALLOWED_RECIPIENTS);
  if (!allowed.length) {
    return;
  }
  const normalizedRecipient = String(recipient || "").toLowerCase();
  if (!allowed.includes(normalizedRecipient)) {
    throw new Error(`Recipient is not allowed: ${recipient}`);
  }
}

export function extractLinks(value) {
  const matches = String(value || "").match(/https?:\/\/[^\s<>"']+/g) || [];
  return [...new Set(matches.map((link) => link.replace(/[).,\]]+$/, "")))];
}

export function parseSimpleMime(rawText) {
  const headers = parseHeaderBlock(rawText.split(/\r?\n\r?\n/, 1)[0] || "");
  const body = rawText.replace(/^[\s\S]*?\r?\n\r?\n/, "");
  const contentType = headers["content-type"] || "";
  if (contentType.includes("text/html")) {
    return {
      subject: headers.subject || "",
      messageId: headers["message-id"] || "",
      date: headers.date || "",
      text: stripHtml(body),
      html: body.trim(),
    };
  }
  return {
    subject: headers.subject || "",
    messageId: headers["message-id"] || "",
    date: headers.date || "",
    text: body.trim(),
    html: "",
  };
}

function parseHeaderBlock(block) {
  const headers = {};
  let active = "";
  for (const line of block.split(/\r?\n/)) {
    if (/^\s/.test(line) && active) {
      headers[active] = `${headers[active]} ${line.trim()}`;
      continue;
    }
    const separator = line.indexOf(":");
    if (separator <= 0) {
      continue;
    }
    active = line.slice(0, separator).toLowerCase();
    headers[active] = line.slice(separator + 1).trim();
  }
  return headers;
}

function header(headers, name) {
  return headers?.get?.(name) || headers?.get?.(name.toLowerCase()) || "";
}

async function readRawBytes(raw) {
  if (!raw) {
    return new Uint8Array();
  }
  const arrayBuffer = await new Response(raw).arrayBuffer();
  return new Uint8Array(arrayBuffer);
}

function decodeUtf8(bytes) {
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

function base64Encode(bytes) {
  if (typeof Buffer !== "undefined") {
    return Buffer.from(bytes).toString("base64");
  }
  let binary = "";
  const chunkSize = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += chunkSize) {
    binary += String.fromCharCode(...bytes.slice(offset, offset + chunkSize));
  }
  return btoa(binary);
}

function stripHtml(value) {
  return String(value || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

function normalizeDate(value) {
  const parsed = value ? new Date(value) : new Date();
  if (Number.isNaN(parsed.getTime())) {
    return new Date().toISOString();
  }
  return parsed.toISOString();
}

function splitList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}
