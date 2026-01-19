import { useEffect } from "react";

interface UseResizeObserverOptions<T extends HTMLElement> {
  ref: React.RefObject<T | null>;
  box?: ResizeObserverBoxOptions;
  onResize?: (entry: ResizeObserverEntry) => void;
}

/**
 * Custom hook to observe element resize.
 * Matches the signature expected by Untitled UI components.
 */
export function useResizeObserver<T extends HTMLElement>({
  ref,
  box,
  onResize,
}: UseResizeObserverOptions<T>) {
  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (onResize) {
        onResize(entry);
      }
    });

    observer.observe(element, { box });

    return () => {
      observer.disconnect();
    };
  }, [ref, box, onResize]);
}
