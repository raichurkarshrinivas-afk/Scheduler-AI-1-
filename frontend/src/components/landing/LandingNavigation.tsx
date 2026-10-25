import React, { useState } from 'react';
import { Menu, X, ArrowRight } from 'lucide-react';
import { Button } from '../common/Button';

export interface LandingNavigationProps {
  onLoginClick: () => void;
  onContactClick: () => void;
}

export const LandingNavigation: React.FC<LandingNavigationProps> = ({
  onLoginClick,
  onContactClick,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navLinks = [
    { label: 'Product', href: '#product-modules' },
    { label: 'How it works', href: '#workflow' },
    { label: 'Security', href: '#security' },
    { label: 'FAQ', href: '#faq' },
  ];

  const handleScroll = (href: string) => {
    setMobileMenuOpen(false);
    const el = document.querySelector(href);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <header className="sticky top-0 z-40 w-full bg-surface/90 backdrop-blur-md border-b border-border/80 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Scheduler Wordmark / Brand */}
        <a
          href="#"
          className="flex items-center gap-2.5 select-none focus-visible:outline-2 focus-visible:outline-teal rounded-lg p-1"
          aria-label="Scheduler home"
        >
          <div className="w-8 h-8 rounded-lg bg-teal flex items-center justify-center text-white font-bold text-lg font-heading shadow-subtle">
            S
          </div>
          <div>
            <span className="font-heading font-bold text-lg text-navy tracking-tight">
              Scheduler
            </span>
          </div>
        </a>

        {/* Desktop Navigation Links */}
        <nav className="hidden md:flex items-center gap-8" aria-label="Main Navigation">
          {navLinks.map((link) => (
            <button
              key={link.href}
              onClick={() => handleScroll(link.href)}
              className="text-sm font-medium text-navy-muted hover:text-navy transition-colors focus-visible:outline-2 focus-visible:outline-teal rounded-md px-1 py-0.5"
            >
              {link.label}
            </button>
          ))}
          <button
            onClick={onContactClick}
            className="text-sm font-medium text-navy-muted hover:text-navy transition-colors focus-visible:outline-2 focus-visible:outline-teal rounded-md px-1 py-0.5"
          >
            Contact
          </button>
        </nav>

        {/* Desktop Actions */}
        <div className="hidden md:flex items-center gap-3">
          <Button
            variant="primary"
            size="sm"
            onClick={onLoginClick}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            Log in
          </Button>
        </div>

        {/* Mobile Hamburger Button */}
        <div className="flex md:hidden">
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 rounded-lg text-navy-muted hover:text-navy hover:bg-bg focus-visible:outline-2 focus-visible:outline-teal"
            aria-expanded={mobileMenuOpen}
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile Menu Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden border-b border-border bg-surface px-4 pt-3 pb-6 space-y-3 shadow-card animate-in slide-in-from-top-2 duration-150">
          <div className="space-y-1">
            {navLinks.map((link) => (
              <button
                key={link.href}
                onClick={() => handleScroll(link.href)}
                className="w-full text-left px-3 py-2 text-base font-medium text-navy rounded-lg hover:bg-bg transition-colors"
              >
                {link.label}
              </button>
            ))}
            <button
              onClick={() => {
                setMobileMenuOpen(false);
                onContactClick();
              }}
              className="w-full text-left px-3 py-2 text-base font-medium text-navy rounded-lg hover:bg-bg transition-colors"
            >
              Contact
            </button>
          </div>

          <div className="pt-3 border-t border-border">
            <Button
              variant="primary"
              size="md"
              className="w-full"
              onClick={() => {
                setMobileMenuOpen(false);
                onLoginClick();
              }}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              Log in
            </Button>
          </div>
        </div>
      )}
    </header>
  );
};
