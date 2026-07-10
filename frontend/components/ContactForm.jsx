const contactFields = [
  { label: "First and last name", name: "name", type: "text", required: true },
  { label: "Phone number", name: "phone", type: "tel", required: true },
  { label: "Email", name: "email", type: "email" },
  { label: "Address", name: "address", type: "text" },
];

export default function ContactForm() {
  return (
    <form className="contact-form">
      <div className="contact-field-grid">
        {contactFields.map((field) => (
          <label key={field.name}>
            <span>
              {field.label}
              {field.required ? " *" : ""}
            </span>
            <input name={field.name} type={field.type} required={field.required} />
          </label>
        ))}
      </div>

      <label>
        <span>Message</span>
        <textarea name="message" rows="6" />
      </label>

      <button type="submit">Send inquiry</button>
    </form>
  );
}
