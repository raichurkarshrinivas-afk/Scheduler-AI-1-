import React, { useState } from 'react';
import { LandingNavigation } from '../components/landing/LandingNavigation';
import { HeroSection } from '../components/landing/HeroSection';
import { ProductModules } from '../components/landing/ProductModules';
import { WorkflowSection } from '../components/landing/WorkflowSection';
import { TeacherPreview } from '../components/landing/TeacherPreview';
import { StudentPreview } from '../components/landing/StudentPreview';
import { SecuritySection } from '../components/landing/SecuritySection';
import { FAQSection } from '../components/landing/FAQSection';
import { ContactSection } from '../components/landing/ContactSection';
import { LandingFooter } from '../components/landing/LandingFooter';
import { PrivacyModal, AccessibilityModal } from '../components/LegalModals';

export interface LandingPageProps {
  onLoginClick: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onLoginClick }) => {
  const [privacyOpen, setPrivacyOpen] = useState(false);
  const [accessibilityOpen, setAccessibilityOpen] = useState(false);

  const handleContactClick = () => {
    const el = document.querySelector('#contact');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const handleModuleSelect = (_key?: string) => {
    void _key;
    // Scrolls to the interactive preview / workflow
    const el = document.querySelector('#preview-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-bg text-navy flex flex-col selection:bg-teal-light selection:text-teal">
      {/* 1. Header Navigation */}
      <LandingNavigation
        onLoginClick={onLoginClick}
        onContactClick={handleContactClick}
      />

      <main className="flex-1">
        {/* 2. Hero Section with 3D Scene */}
        <HeroSection onLoginClick={onLoginClick} />

        {/* 3. Three Product Modules */}
        <ProductModules onModuleSelect={handleModuleSelect} />

        {/* 4. Four-Step Workflow */}
        <WorkflowSection />

        {/* 5 & 6. Teacher and Student Previews */}
        <section id="preview-section" className="py-16 sm:py-20 border-b border-border/70 bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-16">
            <div className="text-center max-w-2xl mx-auto">
              <span className="text-xs font-semibold uppercase tracking-wider text-teal bg-teal-light px-3 py-1 rounded-full border border-teal/20">
                Connected Perspectives
              </span>
              <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy tracking-tight mt-3 mb-2">
                Tailored for Faculty and Students Alike
              </h2>
              <p className="text-sm text-navy-muted">
                One verified schedule engine powers distinct, purpose-built interfaces across departments.
              </p>
            </div>

            {/* Teacher Preview */}
            <div className="space-y-4">
              <TeacherPreview />
            </div>

            {/* Student Preview */}
            <div className="space-y-4">
              <StudentPreview />
            </div>
          </div>
        </section>

        {/* 7. Implemented Security Section */}
        <SecuritySection />

        {/* 8. Frequently Asked Questions */}
        <FAQSection />

        {/* 9. Contact / Feedback Section */}
        <ContactSection />
      </main>

      {/* 10. Footer */}
      <LandingFooter
        onPrivacyClick={() => setPrivacyOpen(true)}
        onAccessibilityClick={() => setAccessibilityOpen(true)}
        onContactClick={handleContactClick}
      />

      {/* Legal & Accessibility Modals */}
      <PrivacyModal isOpen={privacyOpen} onClose={() => setPrivacyOpen(false)} />
      <AccessibilityModal
        isOpen={accessibilityOpen}
        onClose={() => setAccessibilityOpen(false)}
      />
    </div>
  );
};
