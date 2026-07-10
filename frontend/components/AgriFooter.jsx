import Link from "next/link";

const footerLinks = [
  { label: "Home", href: "/" },
  { label: "About us", href: "/about" },
  { label: "Services", href: "/services" },
  { label: "Research & collaboration", href: "/research-collaboration" },
  { label: "Contact us", href: "/contact" },
  { label: "Toolkit Dashboard", href: "/console" },
];

export default function AgriFooter() {
  return (
    <footer className="agri-footer">
      <div>
        <p className="story-kicker">Our mission</p>
        <strong>
          To design, support, and sustain farming systems that are resilient by science, grounded
          in ecology, and built for the communities who will inherit the land we share.
        </strong>
      </div>

      <nav aria-label="Footer navigation">
        {footerLinks.map((link) => (
          <Link key={link.href} href={link.href}>
            {link.label}
          </Link>
        ))}
      </nav>
    </footer>
  );
}
