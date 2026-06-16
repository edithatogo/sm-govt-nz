import { simpleParser } from "mailparser";

export default defineComponent({
  async run({ steps, $ }) {
    const event = steps.trigger.event || {};
    const mail = event.mail || event;
    const body = mail.body || event.body || {};

    const asString = (value) => {
      if (!value) return "";
      if (typeof value === "string") return value;
      if (Array.isArray(value)) return value.map(asString).filter(Boolean).join(", ");
      if (value.text) return String(value.text);
      if (value.address) {
        return value.name ? `${value.name} <${value.address}>` : String(value.address);
      }
      if (value.value) return asString(value.value);
      try {
        return JSON.stringify(value);
      } catch {
        return String(value);
      }
    };

    const headerValue = (headers, name) => {
      if (!headers) return "";
      if (typeof headers.get === "function") return asString(headers.get(name));
      const direct = headers[name] || headers[name.toLowerCase()] || headers[name.toUpperCase()];
      return asString(Array.isArray(direct) ? direct[0] : direct);
    };

    let parsed = {};
    let rawMime = "";
    const contentUrl =
      mail.content_url ||
      event.content_url ||
      body.content_url ||
      mail.contentUrl ||
      event.contentUrl ||
      body.contentUrl;

    if (contentUrl) {
      const rawResponse = await fetch(contentUrl);
      if (!rawResponse.ok) {
        throw new Error(
          `Failed to download raw email from Pipedream content_url: ${rawResponse.status}`,
        );
      }
      rawMime = await rawResponse.text();
      parsed = await simpleParser(rawMime);
    }

    const headers = parsed.headers || mail.headers || event.headers || {};
    const text = asString(
      parsed.text ||
        body.text ||
        body.text_body ||
        body.body_text ||
        mail.text ||
        mail.text_body ||
        mail.body_text ||
        event.text ||
        event.text_body ||
        event.body_text,
    );
    const html = asString(
      parsed.html ||
        body.html ||
        body.html_body ||
        body.body_html ||
        mail.html ||
        mail.html_body ||
        mail.body_html ||
        event.html ||
        event.html_body ||
        event.body_html,
    );
    const links = Array.from(
      new Set((text + "\n" + html).match(/https?:\/\/[^\s"'<>]+/g) || []),
    );
    const messageId = asString(
      parsed.messageId ||
        mail.message_id ||
        mail.messageId ||
        event.message_id ||
        event.messageId ||
        headerValue(headers, "message-id") ||
        `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    );
    const receivedAt =
      parsed.date instanceof Date
        ? parsed.date.toISOString()
        : asString(
            mail.received_at ||
              event.received_at ||
              mail.receivedAt ||
              event.receivedAt ||
              new Date().toISOString(),
          );

    const payload = {
      event_type: "courts_nz_email_received",
      client_payload: {
        message_id: messageId,
        from: asString(parsed.from || mail.from || event.from || headerValue(headers, "from")),
        to: asString(parsed.to || mail.to || event.to || headerValue(headers, "to")),
        subject: asString(
          parsed.subject || mail.subject || event.subject || headerValue(headers, "subject"),
        ),
        text,
        html,
        received_at: receivedAt,
        links,
        raw_mime_base64: rawMime ? Buffer.from(rawMime, "utf8").toString("base64") : "",
      },
    };

    const token = process.env.GITHUB_DISPATCH_TOKEN;
    if (!token) throw new Error("Missing GITHUB_DISPATCH_TOKEN Pipedream secret");

    const response = await fetch("https://api.github.com/repos/edithatogo/sm-govt-nz/dispatches", {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(`GitHub repository_dispatch failed: ${response.status} ${await response.text()}`);
    }

    return {
      dispatched: true,
      message_id: payload.client_payload.message_id,
      subject: payload.client_payload.subject,
      text_length: payload.client_payload.text.length,
      html_length: payload.client_payload.html.length,
      raw_mime_base64_length: payload.client_payload.raw_mime_base64.length,
      links: payload.client_payload.links,
    };
  },
});
