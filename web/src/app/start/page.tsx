import { Activity, Clock, MapPin, Users } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import type { CSSProperties } from "react";
import { ChoiceCard } from "@/components/choice-card";
import { IntroHeadline } from "@/components/intro-headline";

export const metadata: Metadata = { title: { absolute: "Get started | Iris Bank" } };

/**
 * The reveal, in milliseconds from page load:
 *   0     blank white screen
 *   400   headline fades in, centred
 *   1900  headline rises to its place (IntroHeadline)
 *   2500  subline fades in
 *   4000  cards fade in, one after the other; then Back and the notice
 */
const delay = (ms: number) => ({ "--intro-delay": `${ms}ms` }) as CSSProperties;

export default function StartPage() {
  return (
    <main id="main" className="relative flex min-h-dvh flex-col bg-white">
      <Link
        href="/"
        style={delay(4500)}
        className="intro-in absolute top-5 left-6 rounded-sm py-2 text-[13px] text-[#4a4a50] underline decoration-[#4a4a50]/40 underline-offset-4 hover:text-black hover:decoration-black sm:left-10 lg:top-8 lg:left-[7vw]"
      >
        Back
      </Link>

      {/* Centred stack below 1280px; from xl, a split: text left, cards right. */}
      <div className="mx-auto flex w-full max-w-[52rem] flex-1 flex-col items-center justify-center gap-8 px-6 py-20 text-center sm:px-10 xl:max-w-none xl:flex-row xl:justify-between xl:gap-16 xl:pr-[6vw] xl:pl-[7vw] xl:text-left">
        <div className="flex flex-col items-center gap-5 xl:max-w-[34rem] xl:items-start xl:gap-7">
          <IntroHeadline className="font-display text-[44px] leading-[0.98] font-extrabold tracking-[-0.02em] italic [font-stretch:112%] w-fit sm:text-[64px] lg:text-[clamp(56px,4.8vw,80px)] xl:text-[clamp(72px,5.4vw,96px)]">
            <span className="intro-in block" style={delay(400)}>
              <span className="whitespace-nowrap text-[#0b0b0c]">Say hello to</span>
              <br />
              <span className="whitespace-nowrap text-[#0b0b0c]">
                your <span className="text-gold">Copilot</span>
              </span>
            </span>
          </IntroHeadline>
          <p style={delay(2500)} className="intro-in max-w-[44ch] text-[18px] leading-relaxed text-[#4a4a50] sm:text-[19px] xl:text-[20px]">
            Built for Relationship Managers. All your clients and their data, in the palm of
            your hand.
          </p>
          <p style={delay(4500)} className="intro-in hidden text-[13px] text-[#4a4a50] xl:block">
            The clients, bankers and money here are synthetic.
          </p>
        </div>

        {/* Both cards wait for their screens (the tour and Today); add href when they exist. */}
        <div className="mt-2 grid w-full max-w-[46rem] gap-5 sm:grid-cols-2 xl:mt-0 xl:max-w-[56rem] xl:flex-1 xl:gap-6">
          <ChoiceCard
            primary
            className="intro-in"
            style={delay(4000)}
            image="/onboarding/tour-banker.jpg"
            imagePosition="40% 35%"
            title="Guided tour"
            subtitle="Best place to start"
            facts={[
              { icon: Clock, children: <>about <b className="font-semibold">2 min</b></> },
              { icon: MapPin, children: <><b className="font-semibold">4</b> stops</> },
            ]}
            action="Start the tour"
          />
          <ChoiceCard
            className="intro-in"
            style={delay(4150)}
            image="/onboarding/explore-coins.jpg"
            title="Explore on your own"
            subtitle="At your own pace"
            facts={[
              { icon: Users, children: <>full <b className="font-semibold">book</b></> },
              { icon: Activity, children: <><b className="font-semibold">5</b> signals</> },
            ]}
            action="Open the app"
          />
        </div>

        <p style={delay(4500)} className="intro-in text-[13px] text-[#4a4a50] xl:hidden">
          The clients, bankers and money here are synthetic.
        </p>
      </div>
    </main>
  );
}
