import type { Metadata } from "next";
import { Button } from "@/components/ui/button";
import { WelcomeVideo } from "@/components/welcome-video";

export const metadata: Metadata = { title: { absolute: "Welcome | Iris Bank" } };

export default function WelcomePage() {
  return (
    <main id="main" className="relative flex min-h-dvh flex-col overflow-hidden bg-white">
      <WelcomeVideo />
      <div className="relative z-10 flex flex-1 flex-col justify-end gap-9 px-6 pt-[62dvh] pb-24 sm:px-10 lg:w-[52%] lg:justify-center lg:py-24 lg:pl-[7vw]">
        <h1 className="font-display text-[48px] leading-[0.98] font-extrabold tracking-[-0.02em] italic [font-stretch:112%] sm:text-[72px] lg:text-[clamp(56px,5.6vw,96px)]">
          <span className="whitespace-nowrap text-[#0b0b0c]">Welcome to</span>
          <br />
          <span className="text-gold whitespace-nowrap">Iris Bank</span>
        </h1>
        {/* Get started has no destination yet: the next screen hasn't been built. */}
        <Button
          disabled
          className="relative h-14 w-full max-w-[18rem] overflow-hidden rounded-full border-black bg-[linear-gradient(180deg,#4a4a4f_0%,#1d1d20_48%,#050506_52%,#1a1a1c_100%)] text-[16px] font-medium text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.35),inset_0_-1px_0_rgba(255,255,255,0.08),0_6px_16px_-6px_rgba(0,0,0,0.55)] before:pointer-events-none before:absolute before:inset-x-4 before:top-[3px] before:h-[45%] before:rounded-full before:bg-[linear-gradient(180deg,rgba(255,255,255,0.32),rgba(255,255,255,0.04))] before:content-[''] disabled:opacity-100"
        >
          <span className="relative">Get started</span>
        </Button>
      </div>
    </main>
  );
}
