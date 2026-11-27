---
name: Iris Bank, welcome look
source: web/src/app/page.tsx, web/src/components/welcome-video.tsx, web/src/app/globals.css
status: set by the welcome screen (commit 442101d); later screens extend it
colors:
  page: "#FFFFFF"
  ink: "#0B0B0C"
  ink-soft: "#4A4A50"
  gold:
    gradient: "linear-gradient(172deg, #8C5A1C 0%, #BF8336 34%, #7E4E16 58%, #B47A30 80%, #8C5A1C 100%)"
    fallback: "#A8702B"
  bronze-edge:
    gradient: "#F3D29A to #C98A3E to #8F5A23 (top to bottom)"
  pill:
    gradient: "linear-gradient(180deg, #4A4A4F 0%, #1D1D20 48%, #050506 52%, #1A1A1C 100%)"
    text: "#FFFFFF"
typography:
  display:
    family: Archivo (Google, variable, wdth axis)
    style: italic
    weight: 800
    stretch: 112%
    tracking: -0.02em
    leading: 0.98
    sizes: { phone: 48px, tablet: 72px, desktop: "clamp(56px, 5.6vw, 96px)" }
  ui:
    family: IBM Plex Sans
    button: 16px / 500
    small: 13px / 400
radius:
  pill: 9999px
layout:
  desktop: "text panel left (52%), video panel right (58%), overlapping on a 26% slant"
  phone: "video panel top (60dvh), bottom edge slants from 84% to 100%; text below"
---

# Iris Bank: welcome look

This is the visual language the welcome screen set. It reads like a premium
metal card: white space, black type, one word in metallic gold, a glossy black
control, and the card itself in motion behind a slanted edge. Use it as the
starting point for the next screens and change it deliberately, not by drift.

## Colour

| Role | Value | Used for | Contrast on white |
| --- | --- | --- | --- |
| Page | `#FFFFFF` | Background of the text panel | n/a |
| Ink | `#0B0B0C` | "Welcome to", primary text | 19.6:1 |
| Ink soft | `#4A4A50` | Secondary links (Pause background video) | 8.9:1 |
| Gold | gradient, `.text-gold` | The brand name only ("Iris Bank") | lightest stop `#BF8336` 3.2:1 |
| Bronze edge | gradient | The 1.5px line on the slanted cut | decorative |
| Pill | black gloss gradient | Primary action (Get started) | white label above 15:1 |

- Gold appears **once per screen**, on the brand name or the single most
  important word. Never on body text: at 3.2:1 it only passes for large text
  (24px and up, or 19px bold).
- The gold for white backgrounds is deliberately deep. The pale gold
  (`#F8E4B4` to `#B57B3C`) only works on black; on white it drops to 1.3:1.
- No colour wash over the video. It plays at full strength.

## Typography

- **Display: Archivo, extra-bold italic, 112% width.** Headlines only, in the
  spirit of the embossed lettering on the card. Each line is set
  `whitespace-nowrap` and the size scales with the viewport so lines never break
  mid-phrase. The italic needs `padding-right: 0.08em` so the last letter is not
  clipped by the gradient fill.
- **UI: IBM Plex Sans.** Buttons 16px medium; small links 13px.
- Mixed case, not capitals. One headline per screen.

## Layout

```
Desktop                                   Phone
┌──────────────────────┬──────────────┐  ┌───────────────┐
│                     /               │  │  [ video ]    │
│  Welcome to        /   [ video ]    │  │_______________/│ ← slant
│  Iris Bank        /                 │  │ Welcome to    │
│  (Get started)   /                  │  │ Iris Bank     │
│                 /                   │  │ (Get started) │
│ Pause video    /                    │  │ Pause video   │
└──────────────────────────────────────┘  └───────────────┘
```

- Text left-aligned, vertically centred on desktop, anchored to the bottom on a
  phone. Left inset `7vw` on desktop, 24 to 40px on smaller screens.
- The **slanted divider** is the signature: `clip-path` on the video panel
  (`polygon(26% 0, 100% 0, 100% 100%, 0 100%)` on desktop,
  `polygon(0 0, 100% 0, 100% 84%, 0 100%)` on a phone), with a bronze SVG line
  drawn along the cut using `vector-effect: non-scaling-stroke`.
- Breakpoint for the split: `lg` (1024px).

## Components

**Primary pill (Get started).** shadcn `Button`, `h-14`, full width up to
`18rem`, `rounded-full`, black gloss gradient with a hard midline at 50%, a
white sheen on the top 45% (`::before`, 32% to 4% white), a 1px inner top
highlight and a soft drop shadow. The label sits in a `relative` span so the
sheen never covers it. One primary pill per screen.

**Video panel.** `<video muted loop playsInline preload="auto">` with WebM then
MP4 sources and a JPEG poster. Started from script, not `autoPlay`, so
reduced-motion visitors get the poster. `aria-hidden`: it is decoration.

**Pause control.** Required for any looping motion (WCAG 2.2.2). A real
`<button>` with `aria-pressed`, styled as a quiet underlined text link in ink
soft, bottom-left of the text panel. Its label follows the video's own
play/pause events.

## Onboarding (`/start`)

The screen after welcome. White, centred, and revealed in sequence.

- **Reveal** (ms from load): 0 blank; 400 headline fades in at the centre of
  the screen; 1900 it rises to its place (`IntroHeadline`, Web Animations,
  1100ms ease-in-out); 2500 subline; 4000 and 4150 the two cards; 4500 Back
  and the notice. Fades use `.intro-in` (globals.css): 900ms, rise 14px from a
  6px blur, delay from `--intro-delay`. Reduced motion: opacity only, no rise.
- **Headline + subline.** The display face holds a short headline only ("Say
  hello to / your Copilot", gold on "Copilot"). Longer copy goes in a Plex Sans
  subline ("Built for Relationship Managers. ..."), 18 to 19px, ink soft, max 44ch. Never set a sentence in the display
  face.
- **Choice cards** (`ChoiceCard`), after a travel-card reference: white, 32px
  radius, 12px inset photo with 24px radius (16:10), 26px semibold title, grey
  `#6B6B72` subtitle, a row of icon + fact (lucide, bold value), and a 52px
  pill at the foot. Soft shadow plus a 1px hairline. Two side by side from
  `sm`, stacked on a phone. The whole card is one link; the pill is drawn
  inside it. Guided tour gets the black gloss pill; Explore the clear `glass` pill
  (see-through, same midline and sheen, ink label).
- **Card photos** (Pexels, resized to 1200px): `tour-banker.jpg`, a banker reviewing
  papers with a client (pexels-rdne-7821680), framed on him with
  `imagePosition="40% 35%"`; `explore-coins.jpg`, a magnifying glass over a world
  map of coins (pexels-gabby-k-7412089).
- **Layout.** Below 1280px: one centred column (headline, subline, cards,
  notice). From `xl` (1280px): a split. Text column left (max 34rem,
  left-aligned, headline up to 96px, subline 20px, notice under it), cards
  right (up to 56rem, side by side), insets 7vw left and 6vw right. The
  headline fades in at the screen centre, then glides up and left into place.
- **Synthetic-data notice** under the cards (or under the subline from `xl`),
  13px ink soft. **Back** top-left.

The gloss pill lives in `button.tsx` as `variant="gloss"` with `size="pill"`;
links use `buttonVariants(...)` on a `<Link>` so they stay links.

## Media

- Source: `That looks nice.mp4` (3200×2400, 4.5s). Only the right half (the
  floating card) is used: `crop=1584:2400:1616:0`, scaled to 1000px wide, 30fps,
  no audio. WebM (VP9, crf 34) 365 KB; MP4 (H.264, crf 25, faststart) 735 KB;
  poster 60 KB. Files live in `web/public/video/`.

## Do and don't

- Do keep one gold word, one display headline and one pill per screen.
- Do let the video or imagery bleed off the edge behind a slanted cut.
- Don't put the display face or gold on paragraphs, labels or numbers.
- Don't add overlays, glows or blurs to the video.
- Don't place white or gold text on the video: its frames range from black to
  light grey, so contrast can't be guaranteed.

## Known gaps

- **Brand clash.** `CLAUDE.md` names navy and the logo's orange as the only
  brand colours. This screen is black, white and gold. Decide which rules the
  working screens, or document how the two meet.
- **Logo.** The Iris Bank petal logo doesn't appear on this screen.
- **Third-party marks in the video.** The card shows an orange chevron logo
  (not Iris Bank's) and a Visa mark. Check the video's licence before
  publishing.
- **Choice cards lead nowhere yet.** Guided tour and Explore on your own are
  shown but inactive (`aria-disabled`, no `href`) until the tour and Today
  screens exist. Pass `href` to `ChoiceCard` then.
