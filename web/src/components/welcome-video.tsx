"use client";

import { useEffect, useRef, useState } from "react";

/**
 * The card video, shown at full strength in a panel with a slanted edge.
 * Desktop: the panel fills the right of the screen and its left edge runs on a
 * diagonal. Phone: the panel sits at the top and its bottom edge slants.
 * A thin bronze line, the colour of the card's edge, marks the cut.
 *
 * Muted and looping (browsers only autoplay muted video). A real button
 * pauses it, because looping motion must be stoppable (WCAG 2.2.2). Visitors
 * who ask for reduced motion see the still poster instead.
 */
export function WelcomeVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      video.play().catch(() => {});
    }
  }, []);

  const toggle = () => {
    const video = ref.current;
    if (!video) return;
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  };

  return (
    <>
      <div
        aria-hidden="true"
        className="absolute inset-x-0 top-0 h-[60dvh] lg:inset-x-auto lg:inset-y-0 lg:right-0 lg:h-auto lg:w-[58%]"
      >
        <div className="absolute inset-0 [clip-path:polygon(0_0,100%_0,100%_84%,0_100%)] lg:[clip-path:polygon(26%_0,100%_0,100%_100%,0_100%)]">
          <video
            ref={ref}
            muted
            loop
            playsInline
            preload="auto"
            poster="/video/welcome-poster.jpg"
            onPlay={() => setPlaying(true)}
            onPause={() => setPlaying(false)}
            className="size-full object-cover"
          >
            <source src="/video/welcome.webm" type="video/webm" />
            <source src="/video/welcome.mp4" type="video/mp4" />
          </video>
        </div>
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="pointer-events-none absolute inset-0 size-full overflow-visible"
        >
          <defs>
            <linearGradient id="bronze-edge" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#f3d29a" />
              <stop offset="0.5" stopColor="#c98a3e" />
              <stop offset="1" stopColor="#8f5a23" />
            </linearGradient>
          </defs>
          {/* Phone: bottom edge */}
          <line x1="0" y1="100" x2="100" y2="84" stroke="url(#bronze-edge)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" className="lg:hidden" />
          {/* Desktop: left edge */}
          <line x1="26" y1="0" x2="0" y2="100" stroke="url(#bronze-edge)" strokeWidth="1.5" vectorEffect="non-scaling-stroke" className="hidden lg:block" />
        </svg>
      </div>

      <button
        type="button"
        onClick={toggle}
        aria-pressed={!playing}
        className="absolute bottom-5 left-6 z-10 rounded-md py-2 text-[13px] text-[#4a4a50] underline decoration-[#4a4a50]/40 underline-offset-4 hover:text-black hover:decoration-black sm:left-10 lg:bottom-8 lg:left-[7vw]"
      >
        {playing ? "Pause background video" : "Play background video"}
      </button>
    </>
  );
}
