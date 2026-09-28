"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const links = [
  { label: "Home", href: "/" },
  { label: "About us", href: "/about" },
  { label: "Services", href: "/services" },
  {
    label: "Products",
    href: "/products",
    children: [
      { label: "The Urban Farmer Project", href: "/products/urban-farmer-project" },
      { label: "The Miachi Project", href: "/products/miachi-project" },
    ],
  },
  { label: "Research collaboration", href: "/research-collaboration" },
  { label: "Analytics", href: "/analytics" },
  { label: "Toolkit Console", href: "/console" },
  { label: "Contact us", href: "/contact" },
];

export default function AgriPageNav() {
  const [isOpen, setIsOpen] = useState(false);
  const [isProductsOpen, setIsProductsOpen] = useState(false);
  const pathname = usePathname();

  return (
    <header className={`agri-page-nav${isOpen ? " is-open" : ""}`}>
      <Link className="agri-page-brand" href="/" aria-label="SusBiome home">
        <Image
          src="/images/susbiome-logo.png"
          alt="SusBiome"
          width={58}
          height={47}
          priority
          unoptimized
          quality={100}
        />
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
        {links.map((link) => {
          const isActive = link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          if (link.children) {
            return (
              <div className={`agri-nav-group${isProductsOpen ? " is-open" : ""}`} key={link.href}>
                <button
                  type="button"
                  className={isActive ? "is-active" : undefined}
                  aria-expanded={isProductsOpen}
                  aria-controls="products-submenu"
                  onClick={() => setIsProductsOpen((value) => !value)}
                >
                  {link.label}
                  <span className="agri-nav-caret" aria-hidden="true">⌄</span>
                </button>
                <div id="products-submenu" className="agri-nav-submenu" aria-label={`${link.label} submenu`}>
                  {link.children.map((child) => (
                    <Link
                      className={pathname === child.href ? "is-active" : undefined}
                      key={child.href}
                      href={child.href}
                      onClick={() => {
                        setIsOpen(false);
                        setIsProductsOpen(false);
                      }}
                    >
                      {child.label}
                    </Link>
                  ))}
                </div>
              </div>
            );
          }
          return (
            <Link
              className={isActive ? "is-active" : undefined}
              key={link.href}
              href={link.href}
              onClick={() => setIsOpen(false)}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
