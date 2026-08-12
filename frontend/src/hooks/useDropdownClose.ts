import { useEffect, useRef } from 'react';

/**
 * Closes an open dropdown/menu when the user:
 *  - clicks anywhere outside the referenced element
 *  - scrolls anywhere outside the referenced element (e.g. the page behind
 *    a fixed/absolute dropdown panel)
 *  - presses Escape
 *
 * Usage:
 *   const ref = useDropdownClose<HTMLDivElement>(isOpen, () => setIsOpen(false));
 *   <div ref={ref}> ...trigger + dropdown panel... </div>
 *
 * Listeners are only attached while `isOpen` is true, and everything is
 * cleaned up on close/unmount - so opening a second dropdown that also uses
 * this hook naturally closes the first one instead of stacking listeners.
 */
export function useDropdownClose<T extends HTMLElement = HTMLElement>(
  isOpen: boolean,
  onClose: () => void
) {
  const ref = useRef<T>(null);

  useEffect(() => {
    if (!isOpen) return;

    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        onClose();
      }
    };

    const handleScroll = (event: Event) => {
      // Ignore scroll events that originate *inside* the dropdown itself
      // (e.g. a scrollable option list) so selecting an option doesn't
      // immediately close the panel.
      if (ref.current && event.target instanceof Node && ref.current.contains(event.target)) {
        return;
      }
      onClose();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('touchstart', handlePointerDown);
    // capture:true so this fires for scrolls on any scrollable ancestor,
    // not just window scroll
    document.addEventListener('scroll', handleScroll, true);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('touchstart', handlePointerDown);
      document.removeEventListener('scroll', handleScroll, true);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  return ref;
}
