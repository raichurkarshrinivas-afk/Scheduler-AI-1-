import { useEffect, RefObject } from 'react';

export function useKeyboardTrap(
  isOpen: boolean,
  containerRef: RefObject<HTMLElement>,
  onClose?: () => void
) {
  useEffect(() => {
    if (!isOpen || !containerRef.current) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onClose) {
        e.preventDefault();
        onClose();
        return;
      }

      if (e.key === 'Tab') {
        const focusable = containerRef.current?.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (!focusable || focusable.length === 0) return;

        const firstElement = focusable[0];
        const lastElement = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    // Initial focus on first interactive element or container
    const initialFocus = containerRef.current.querySelector<HTMLElement>(
      'button, input, [tabindex]:not([tabindex="-1"])'
    );
    if (initialFocus) {
      initialFocus.focus();
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, containerRef, onClose]);
}
