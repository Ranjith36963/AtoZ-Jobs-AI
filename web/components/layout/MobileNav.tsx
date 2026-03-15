"use client";

import Link from "next/link";

interface MobileNavProps {
  isOpen: boolean;
  onClose: () => void;
}

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/search", label: "Search" },
  { href: "/transparency", label: "Transparency" },
] as const;

export function MobileNav({ isOpen, onClose }: MobileNavProps) {
  if (!isOpen) return null;

  return (
    <div id="mobile-menu" className="border-t border-gray-200 sm:hidden">
      <ul className="space-y-1 px-4 py-3" role="list">
        {NAV_LINKS.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="block rounded-md px-3 py-2 text-base font-medium text-gray-700 hover:bg-gray-100"
              onClick={onClose}
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
