import { useState, useEffect, RefObject } from 'react';

export function useElementVisibility(ref: RefObject<HTMLElement>): boolean {
  const [isVisible, setIsVisible] = useState<boolean>(true);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.05 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [ref]);

  return isVisible;
}
