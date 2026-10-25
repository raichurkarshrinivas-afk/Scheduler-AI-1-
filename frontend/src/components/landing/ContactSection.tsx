import React, { useState } from 'react';
import { Send, CheckCircle2, AlertTriangle, ShieldCheck, Lock, HelpCircle } from 'lucide-react';
import { Card } from '../common/Card';
import { FormField, Input, Select, Textarea } from '../common/FormField';
import { Button } from '../common/Button';
import { Dialog } from '../common/Dialog';
import { api } from '../../services/api';
import { PublicFeedbackCategory } from '../../types';

export const ContactSection: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    category: 'GENERAL_INQUIRY' as PublicFeedbackCategory,
    subject: '',
    message: '',
    honeypot: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successInfo, setSuccessInfo] = useState<{
    referenceCode: string;
    message: string;
  } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!formData.subject.trim() || formData.subject.trim().length < 3) {
      setErrorMsg('Subject must be at least 3 characters.');
      return;
    }
    if (!formData.message.trim() || formData.message.trim().length < 10) {
      setErrorMsg('Message must be at least 10 characters.');
      return;
    }
    if (formData.message.length > 5000) {
      setErrorMsg('Message cannot exceed 5,000 characters.');
      return;
    }

    setIsSubmitting(true);
    try {
      const resp = await api.feedback.submitPublic({
        name: formData.name.trim() || undefined,
        email: formData.email.trim() || undefined,
        category: formData.category,
        subject: formData.subject.trim(),
        message: formData.message.trim(),
        honeypot: formData.honeypot || undefined,
      });

      setSuccessInfo({
        referenceCode: resp.reference_code,
        message: resp.message,
      });
      setFormData({
        name: '',
        email: '',
        category: 'GENERAL_INQUIRY',
        subject: '',
        message: '',
        honeypot: '',
      });
    } catch (err: any) {
      if (err.message && err.message.includes('429')) {
        setErrorMsg('Rate limit exceeded. Please wait a few moments before submitting again.');
      } else {
        setErrorMsg(err.message || 'Unable to submit your inquiry. Please verify inputs and try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section id="contact" className="py-16 sm:py-20 border-b border-border/70 bg-bg/50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-xl mx-auto mb-10">
          <span className="text-xs font-semibold uppercase tracking-wider text-teal bg-teal-light px-3 py-1 rounded-full border border-teal/20">
            Public Inquiries & Contact
          </span>
          <h2 className="font-heading text-2xl sm:text-3xl font-bold text-navy tracking-tight mt-3 mb-2">
            Contact & General Inquiries
          </h2>
          <p className="text-sm text-navy-muted">
            Reach out regarding pilot trials, timetable integration questions, accessibility support, or general platform inquiries.
          </p>
        </div>

        <Card className="bg-white max-w-2xl mx-auto shadow-sm">
          {/* Privacy Notice Banner */}
          <div className="mb-5 p-3.5 rounded-lg bg-teal-light/40 border border-teal/20 text-xs text-navy flex items-start gap-2.5">
            <ShieldCheck className="w-4 h-4 text-teal shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <strong className="block font-semibold text-teal-dark">Privacy Notice:</strong>
              <span>
                Contact details (name and email) are optional. Inquiries are stored strictly for operational response and technical support. We never share or expose your contact data.
              </span>
            </div>
          </div>

          {/* Security Warning Banner */}
          <div className="mb-5 p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2.5">
            <Lock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <strong className="block font-semibold text-amber-800">Security Guideline:</strong>
              <span>
                Please do not include passwords, authentication credentials, or sensitive student records in public inquiry messages.
              </span>
            </div>
          </div>

          {errorMsg && (
            <div className="mb-5 p-3.5 rounded-lg bg-coral-light/60 border border-coral/30 text-xs text-coral font-medium flex items-start gap-2" role="alert">
              <AlertTriangle className="w-4 h-4 text-coral shrink-0 mt-0.5" aria-hidden="true" />
              <div>{errorMsg}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Honeypot field (hidden from legitimate users, trapped for automated bots) */}
            <div style={{ display: 'none' }} aria-hidden="true">
              <label htmlFor="website_check">Leave this field blank</label>
              <input
                id="website_check"
                type="text"
                name="honeypot"
                value={formData.honeypot}
                onChange={(e) => setFormData({ ...formData, honeypot: e.target.value })}
                tabIndex={-1}
                autoComplete="off"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField
                label="Full Name (Optional)"
                htmlFor="contact-name"
                helperText="You may submit anonymously if preferred"
              >
                <Input
                  id="contact-name"
                  placeholder="e.g. Dr. Arthur Pendelton"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  maxLength={100}
                />
              </FormField>

              <FormField
                label="Email Address (Optional)"
                htmlFor="contact-email"
                helperText="Required only if you request a response"
              >
                <Input
                  id="contact-email"
                  type="email"
                  placeholder="coordinator@institution.edu"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </FormField>
            </div>

            <FormField label="Inquiry Category" htmlFor="contact-category" required>
              <Select
                id="contact-category"
                value={formData.category}
                onChange={(e) => setFormData({ ...formData, category: e.target.value as PublicFeedbackCategory })}
                required
              >
                <option value="GENERAL_INQUIRY">General Inquiry</option>
                <option value="PILOT_REQUEST">Pilot / Deployment Onboarding</option>
                <option value="BUG_REPORT">System Bug / Technical Defect</option>
                <option value="ACCESSIBILITY">Accessibility Inquiries</option>
                <option value="OTHER">Other Inquiry</option>
              </Select>
            </FormField>

            <FormField
              label="Subject"
              htmlFor="contact-subject"
              required
              helperText={`${formData.subject.length}/200 characters`}
            >
              <Input
                id="contact-subject"
                placeholder="Summary of your question or feedback"
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                maxLength={200}
                required
              />
            </FormField>

            <FormField
              label="Message Content"
              htmlFor="contact-message"
              required
              helperText={`${formData.message.length}/5000 characters (min 10 characters)`}
            >
              <Textarea
                id="contact-message"
                rows={5}
                placeholder="Provide your detailed feedback, scheduling inquiry, or technical question..."
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                maxLength={5000}
                required
              />
            </FormField>

            <div className="p-3 rounded-lg bg-bg border border-border/80 text-[11px] text-navy-subtle flex items-start gap-2">
              <HelpCircle className="w-3.5 h-3.5 text-navy-subtle shrink-0 mt-0.5" aria-hidden="true" />
              <span>
                Note: Email confirmation is dispatched only if an email address is provided and the server email provider is actively configured. Your submission is securely persisted immediately regardless of email status.
              </span>
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                type="submit"
                variant="primary"
                size="md"
                isLoading={isSubmitting}
                className="flex items-center gap-2"
              >
                <Send className="w-4 h-4" aria-hidden="true" />
                <span>Submit Inquiry</span>
              </Button>
            </div>
          </form>
        </Card>
      </div>

      {/* Generic Confirmation Dialog */}
      <Dialog
        isOpen={!!successInfo}
        onClose={() => setSuccessInfo(null)}
        title="Inquiry Submitted Successfully"
        footer={
          <Button variant="primary" size="sm" onClick={() => setSuccessInfo(null)}>
            Close
          </Button>
        }
      >
        <div className="space-y-4 text-xs">
          <div className="flex items-start gap-3 p-3.5 bg-teal-light/50 border border-teal/20 rounded-xl">
            <CheckCircle2 className="w-6 h-6 text-teal shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <p className="font-semibold text-teal-dark text-sm mb-1">
                {successInfo?.message || 'Your inquiry has been received securely.'}
              </p>
              <p className="text-navy-muted leading-relaxed">
                A platform administrator will review your message. No internal database records or system internals are exposed.
              </p>
            </div>
          </div>

          <div className="p-3.5 bg-surface border border-border rounded-xl space-y-1.5">
            <span className="text-[11px] uppercase tracking-wider text-navy-subtle font-semibold block">
              Public Submission Reference Code:
            </span>
            <div className="font-mono font-bold text-base text-navy tracking-wider select-all bg-white px-3 py-1.5 rounded border border-border/80 inline-block">
              {successInfo?.referenceCode}
            </div>
            <p className="text-[11px] text-navy-subtle pt-1">
              Keep this reference code for future follow-up regarding your inquiry.
            </p>
          </div>
        </div>
      </Dialog>
    </section>
  );
};
