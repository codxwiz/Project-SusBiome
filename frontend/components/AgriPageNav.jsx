"use client";

import Link from "next/link";
import { useState } from "react";

const links = [
  { label: "Home", href: "/" },
  { label: "About us", href: "/about" },
  { label: "Services", href: "/services" },
  { label: "Research & collaboration", href: "/research-collaboration" },
  { label: "Contact us", href: "/contact" },
];

export default function AgriPageNav() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <header className={`agri-page-nav${isOpen ? " is-open" : ""}`}>
      <Link className="agri-page-brand" href="/">
        SusBiome
      </Link>
      <button
        className="agri-menu-toggle"
        type="button"
        aria-label="Toggle navigation menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((value) => !value)}
      >
        <span></span>
        <span></span>
        <span></span>
      </button>
      <nav aria-label="Page navigation">
        {links.map((link) => (
          <Link key={link.href} href={link.href} onClick={() => setIsOpen(false)}>
            {link.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
