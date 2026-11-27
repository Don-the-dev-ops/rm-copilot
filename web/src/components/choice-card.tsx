import type { LucideIcon } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type Fact = { icon: LucideIcon; children: ReactNode };

type ChoiceCardProps = {
  title: string;
  subtitle: string;
  image: string;
  facts: Fact[];
  /** Text on the pill at the foot of the card. */
  action: string;
  /** Where the card leads. Leave out while the destination isn't built yet. */
  href?: string;
  /** CSS object-position for the photo, to keep its subject in frame. */
  imagePosition?: string;
  /** The recommended choice gets the black gloss pill; the other the clear glass pill. */
  primary?: boolean;
  className?: string;
  style?: CSSProperties;
};

/**
 * One option on the onboarding screen, after a travel-card reference: a white
 * card with deep rounded corners, an inset photo, a bold title, a grey
 * subtitle, a row of small facts and a pill at the foot.
 *
 * The whole card is a single link (one tab stop, one click target). The pill is
 * drawn inside it, not a second button: a button inside a link is invalid.
 */
export function ChoiceCard({ title, subtitle, image, imagePosition = "50% 50%", facts, action, href, primary = false, className, style }: ChoiceCardProps) {
  const content = (
    <>
      <span className="relative block aspect-[16/10] overflow-hidden rounded-[24px] bg-neutral-200">
        <Image
          src={image}
          alt=""
          fill
          sizes="(min-width: 1280px) 440px, (min-width: 640px) 360px, 100vw"
          style={{ objectPosition: imagePosition }}
          className="object-cover transition-transform duration-500 ease-out group-hover/card:scale-[1.03]"
        />
      </span>
      <span className="flex flex-1 flex-col px-3 pt-5 pb-2">
        <span className="text-[26px] leading-tight font-semibold tracking-[-0.02em] text-[#0b0b0c]">{title}</span>
        <span className="mt-1 text-[15px] text-[#6b6b72]">{subtitle}</span>
        <span className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-[15px] text-[#0b0b0c]">
          {facts.map(({ icon: Icon, children }, i) => (
            <span key={i} className="inline-flex items-center gap-2">
              <Icon aria-hidden="true" className="size-[18px] stroke-[1.75] text-[#6b6b72]" />
              <span>{children}</span>
            </span>
          ))}
        </span>
        <span
          className={cn(
            "mt-6",
            primary
              ? buttonVariants({ variant: "gloss", size: "pill" })
              : buttonVariants({ variant: "glass", size: "pill" }),
            "h-[52px] w-full",
          )}
        >
          <span className="relative">{action}</span>
        </span>
      </span>
    </>
  );

  const classes = cn(
    "group/card flex flex-col rounded-[32px] bg-white p-3 text-left outline-none",
    "shadow-[0_0_0_1px_rgba(11,11,12,0.06),0_24px_48px_-28px_rgba(11,11,12,0.35)] transition-shadow duration-300",
    "hover:shadow-[0_0_0_1px_rgba(11,11,12,0.1),0_28px_56px_-26px_rgba(11,11,12,0.45)]",
    "focus-visible:ring-3 focus-visible:ring-[#0b0b0c]/40 focus-visible:ring-offset-4",
    className,
  );

  if (!href) {
    // Destination not built yet: shown, but not a working link.
    return (
      <a aria-disabled="true" className={classes} style={style}>
        {content}
      </a>
    );
  }

  return (
    <Link href={href} className={classes} style={style}>
      {content}
    </Link>
  );
}
