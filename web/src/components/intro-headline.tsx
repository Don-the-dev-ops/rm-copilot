"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";

/** When the headline starts moving from the centre to its place (ms). */
export const LIFT_AT = 1900;
const LIFT_FOR = 1100;

/**
 * The onboarding headline. It fades in (CSS, see `.intro-in`) in the middle of
 * the screen, holds, then glides to its place: straight up on narrower screens,
 * up and to the left on wide ones (the split layout).
 *
 * The page is laid out in its final shape from the start. On mount we measure
 * how far the headline sits from the centre of the screen and hold it offset
 * by that distance until LIFT_AT, then let it glide home. If script hasn't
 * run, it simply appears in place. Reduced motion: no glide.
 */
export function IntroHeadline({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLHeadingElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const box = el.getBoundingClientRect();
    const dx = window.innerWidth / 2 - (box.left + box.width / 2);
    const dy = window.innerHeight / 2 - (box.top + box.height / 2);
    if (Math.abs(dx) < 4 && Math.abs(dy) < 4) return;
    const lift = el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }], {
      delay: LIFT_AT,
      duration: LIFT_FOR,
      easing: "cubic-bezier(0.65, 0, 0.35, 1)",
      fill: "backwards",
    });
    return () => lift.cancel();
  }, []);

  return (
    <h1 ref={ref} className={className}>
      {children}
    </h1>
  );
}
