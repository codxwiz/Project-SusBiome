import Link from "next/link";
import { legalPages } from "../lib/legalPages";

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

      <address className="agri-footer-contact" aria-label="Contact information">
        <p>
          <span>Address</span>
          Kairang, Maning Leikai, Heingang Block
          <br />
          Imphal East Manipur - 795002
        </p>
        <p>
          <span>Email</span>
          <a href="mailto:susbiome098@gmail.com">susbiome098@gmail.com</a>
        </p>
        <p>
          <span>Hours</span>
          Monday - Saturday 10AM - 5PM
        </p>
      </address>

      <nav className="agri-footer-legal" aria-label="Legal documents">
        {legalPages.map((page) => (
          <Link key={page.slug} href={`/legal/${page.slug}`}>
            {page.shortTitle}
          </Link>
        ))}
      </nav>

      <p className="agri-footer-copyright">©2026 SusBiome. All rights reserved.</p>
    </footer>
  );
}
