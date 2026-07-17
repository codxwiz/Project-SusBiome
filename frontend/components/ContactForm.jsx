"use client";

import { useState } from "react";

const contactFields = [
  {
    label: "First and last name",
    name: "name",
    type: "text",
    required: true,
    autoComplete: "name",
    maxLength: 120,
  },
  {
    label: "Phone number",
    name: "phone",
    type: "tel",
    required: true,
    autoComplete: "tel",
    maxLength: 40,
  },
  {
    label: "Email",
    name: "email",
    type: "email",
    autoComplete: "email",
    maxLength: 254,
  },
  {
    label: "Address",
    name: "address",
    type: "text",
    autoComplete: "street-address",
    maxLength: 300,
  },
];

function defaultApiBase() {
  if (typeof window === "undefined") {
    return "";
  }
  if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  return "https://dashboard.susbiome.com";
}

export default function ContactForm() {
  const [submission, setSubmission] = useState({ state: "idle", message: "" });
  const isSending = submission.state === "sending";

  async function handleSubmit(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form).entries());
    const configuredBase = String(process.env.NEXT_PUBLIC_SUSBIOME_API_BASE || "").replace(/\/$/, "");
    const apiBase = configuredBase || defaultApiBase();

    setSubmission({ state: "sending", message: "Sending your enquiry..." });

    try {
      const response = await fetch(`${apiBase}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(values),
      });

      if (!response.ok) {
        throw new Error("The enquiry could not be sent.");
      }

      form.reset();
      setSubmission({
        state: "success",
        message: "Enquiry sent successfully. SusBiome will contact you soon.",
      });
    } catch {
      setSubmission({
        state: "error",
        message: "We could not send your enquiry right now. Please try again shortly.",
      });
    }
  }

  return (
    <form className="contact-form" onSubmit={handleSubmit}>
      <div className="contact-field-grid">
        {contactFields.map((field) => (
          <label key={field.name}>
            <span>
              {field.label}
              {field.required ? " *" : ""}
            </span>
            <input
              name={field.name}
              type={field.type}
              required={field.required}
              autoComplete={field.autoComplete}
              maxLength={field.maxLength}
            />
          </label>
        ))}
      </div>

      <label>
        <span>Message</span>
        <textarea name="message" rows="6" maxLength={4000} />
      </label>

      <div className="contact-form__honeypot" aria-hidden="true">
        <label>
          Website
          <input name="website" type="text" tabIndex={-1} autoComplete="off" />
        </label>
      </div>

      <button type="submit" disabled={isSending}>
        {isSending ? "Sending..." : "Send enquiry"}
      </button>

      <p
        className={`contact-form__status contact-form__status--${submission.state}`}
        role="status"
        aria-live="polite"
      >
        {submission.message}
      </p>
    </form>
  );
}
