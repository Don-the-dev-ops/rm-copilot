import type { Metadata } from "next";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
        {/* A link styled as the pill: it navigates, so it is an <a>, not a button. */}
        <Link href="/start" className={cn(buttonVariants({ variant: "gloss", size: "pill" }), "w-full max-w-[18rem]")}>
          <span className="relative">Get started</span>
        </Link>
      </div>
    </main>
  );
}
