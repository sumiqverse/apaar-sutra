# Design System Specification (Figma Marketing Canvas)

## Overview

Figma's marketing canvas is, at the system level, an editor-clean black-and-white frame. The chrome — top nav, body type, footer, primary CTA — is monochrome. Headlines are oversized `{typography.display-xl}` set in `figmaSans` with aggressive negative tracking, body copy hovers around weight 320–340 of the same variable family, and small mono `{typography.eyebrow}` and `{typography.caption}` labels (figmaMono, all-caps, positive tracking) act as section markers. Every CTA is a pill — `{rounded.pill}` — and the primary action across the entire site is the same black `{components.button-primary}` paired with the same white `{components.button-secondary}`.

What makes the design unique is what happens **between** those monochrome bookends: the page repeatedly drops into oversized pastel **color-block sections** — lime, lavender, cream, mint, pink, coral, and a deep navy — that span the full content width with `{rounded.lg}` corners and `{spacing.xxl}` interior padding. These blocks are where the storytelling lives. They aren't accents tucked into a card; they take over a whole viewport's worth of vertical space, like a designer arranging giant sticky notes on a clean wall. FigJam is the most pastel-saturated, the home page rotates through the full set, and the pricing page ends with a lime FAQ panel — same vocabulary, different rhythm per route.

This is a system built on contrast: the monochrome chrome makes the color blocks feel intentional rather than decorative, and the color blocks make the monochrome chrome feel like editorial paper rather than enterprise SaaS. Density is generous, line-heights are tight on display sizes, and the interface never reaches for shadows or gradients to do the work that color blocks and confident typography already do.

**Key Characteristics:**
- Monochrome system core: `{colors.primary}` (black) and `{colors.canvas}` (white) carry every CTA, every body line, every footer link.
- Oversized pastel **color-block sections** (`{colors.block-lime}`, `{colors.block-lilac}`, `{colors.block-cream}`, `{colors.block-mint}`, `{colors.block-pink}`, `{colors.block-coral}`, `{colors.block-navy}`) define the narrative rhythm of every long-form page.
- Pill is the only button shape — `{rounded.pill}` for text CTAs, `{rounded.full}` for icon buttons. No square buttons anywhere.
- `figmaSans` variable typeface used at unusually fine weight increments (320, 330, 340, 450, 480, 540) — the type system reads as a single voice that flexes rather than a multi-weight family.
- Tight negative letter-spacing on display sizes (-1.72px at 86px, -0.96px at 64px) creates a confident editorial cadence.
- `figmaMono` reserved for category labels, eyebrows, and captions — always uppercase, positive tracking — to flag taxonomy without competing with display type.
- Color-block page rhythm (home): white hero → marquee strip → white feature → lime systems block → navy ship-products block → coral developer block → white template grid → white footer.

## Colors

> Source pages: figma.com (home), /design/, /figjam/brainstorming-tool/, /pricing/, /contact/.

### Brand & Accent
- **Black** (`{colors.primary}`): `#000000` — The system primary. Every primary CTA, every headline, every body line, the marquee strip, the inverse canvas of dark sections.
- **White** (`{colors.on-primary}`): `#FFFFFF` — Inverse text on black surfaces; also the canvas color used as the foreground of secondary pill buttons (`{components.button-secondary}`).
- **Magenta Promo** (`{colors.accent-magenta}`): `#FF2F7C` — A single saturated CTA pink reserved for promotional inline buttons — appears, for example, on the lilac "Save your spot" Release Notes banner. Use scarcely; it is not a section color.

### Surface
- **Canvas** (`{colors.canvas}`): `#FFFFFF` — Default page background and the body of every white card.
- **Inverse Canvas** (`{colors.inverse-canvas}`): `#000000` — Footer, marquee strip, and a subset of "ship products"-style story sections.
- **Surface Soft** (`{colors.surface-soft}`): `#F5F5F5` — Off-white tile background used for icon buttons, template cards, and feature illustration tiles when they sit on the white canvas.
- **Hairline** (`{colors.hairline}`): `#E5E5E5` — 1px borders on form inputs, pricing cards, and table dividers.
- **Hairline Soft** (`{colors.hairline-soft}`): `#F0F0F0` — Even subtler dividers — comparison-table row separators and footer column rules.
- **Block Lime** (`{colors.block-lime}`): `#D4FF5B` (or `#C5FF4A`) — The signature **systems / FAQ / contact-form** color block. Recurs across home, pricing, contact.
- **Block Lilac** (`{colors.block-lilac}`): `#E5D4FF` (or `#D9B8FF`) — Hero block on `/design/`; also the inline Release Notes promo banner.
- **Block Cream** (`{colors.block-cream}`): `#FFF5EA` (or `#FFF7E6`) — Soft warm background — FigJam hero strip, template-grid section.
- **Block Mint** (`{colors.block-mint}`): `#D2F8E7` (or `#C3F4D8`) — FigJam pastel section.
- **Block Pink** (`{colors.block-pink}`): `#FFD6E8` (or `#FFCEE4`) — FigJam pastel section.
- **Block Coral** (`{colors.block-coral}`): `#FF8577` (or `#FF7262`) — "Ship products" coral story block on home.
- **Block Navy** (`{colors.block-navy}`): `#0C1033` (or `#13183F`) — Deep indigo story block — only place dark surfaces appear above the footer.

### Text
- **Ink** (`{colors.ink}`): `#000000` — All headline, body, and caption type on light surfaces. There is no softer mid-gray text role on marketing — body copy is always black at weight 320–340, and weight (not opacity) carries the hierarchy.
- **Inverse Ink** (`{colors.inverse-ink}`): `#FFFFFF` — Type on inverse-canvas surfaces (footer, marquee strip, navy color block).
- **On-Inverse Soft** (`{colors.on-inverse-soft}`): `rgba(255, 255, 255, 0.16)` — White used at ~16% opacity for circular icon-button surfaces against dark sections.

### Semantic
- **Success Green** (`{colors.semantic-success}`): `#0FA958` — Comparison-table checkmarks on pricing. Used as a glyph fill, not a surface.
- **Overlay Scrim** (`{colors.overlay-scrim}`): `rgba(0, 0, 0, 0.60)` — Black used at ~60% opacity behind modal / video-overlay surfaces.

## Typography

### Font Family

- **figmaSans** — Figma's proprietary variable typeface; fallback stack `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`. Variable weight axis is exercised at unusually fine increments (320, 330, 340, 450, 480, 540, 700) — the design system reads as a single voice modulating rather than a stepped weight family.
- **figmaMono** — Monospace; fallback `JetBrains Mono, "SF Mono", Menlo, Consolas, monospace`. Used exclusively for eyebrow labels and captions, always uppercase with positive letter-spacing.

### Hierarchy

| Token | Size | Weight | Line Height | Letter Spacing | Use |
|---|---|---|---|---|---|
| `{typography.display-xl}` | 86px | 340 | 1.00 | -1.72px | Hero headlines (home, FigJam) |
| `{typography.display-lg}` | 64px | 340 | 1.10 | -0.96px | Section opener headlines |
| `{typography.headline}` | 26px | 540 | 1.35 | -0.26px | Story-block titles inside color blocks |
| `{typography.subhead}` | 26px | 340 | 1.35 | -0.26px | Long-form intro paragraphs that sit at near-headline scale |
| `{typography.card-title}` | 24px | 700 | 1.45 | 0 | Pricing-tier titles, feature card titles |
| `{typography.body-lg}` | 20px | 330 | 1.40 | -0.14px | Lead body copy on hero, contact form labels |
| `{typography.body}` | 18px | 320 | 1.45 | -0.26px | Default body |
| `{typography.body-sm}` | 16px | 330 | 1.45 | -0.14px | Card body, footer link list |
| `{typography.link}` | 20px | 480 | 1.40 | -0.10px | Inline link emphasis |
| `{typography.button}` | 20px | 480 | 1.40 | -0.10px | All pill buttons, primary and secondary |
| `{typography.eyebrow}` | 18px | 400 | 1.30 | 0.54px | figmaMono uppercase section eyebrows |
| `{typography.caption}` | 12px | 400 | 1.00 | 0.60px | figmaMono uppercase captions, footer column heads |

## Layout & Spacing

- **Base unit**: 8px.
- Spacing tokens: `hair` (1px), `xxs` (4px), `xs` (8px), `sm` (12px), `md` (16px), `lg` (24px), `xl` (32px), `xxl` (48px), `section` (96px).
- Section interior padding: `{spacing.xxl}` (48px) on color-block sections.
- Universal rhythm constant: `{spacing.section}` (96px) between major content sections returning to white canvas.
- Max content width: `1280px` with responsive gutters.

## Shapes & Radius Scale

| Token | Value | Use |
|---|---|---|
| `{rounded.xs}` | 2px | Anchor / link decoration corners |
| `{rounded.sm}` | 6px | Small chips, sub-nav tabs |
| `{rounded.md}` | 8px | Form inputs, list items, image frames |
| `{rounded.lg}` | 24px | Pricing cards, color-block sections, large image containers |
| `{rounded.xl}` | 32px | Hero feature panels, oversized callouts |
| `{rounded.pill}` | 50px / 9999px | All text CTAs (primary, secondary, tab toggles) |
| `{rounded.full}` | 9999px | Circular icon buttons, comparison checkmark glyphs |

## Key Components

1. **`button-primary`**: Black `#000000`, white text, rounded pill, font-weight 480, padding 10px 20px.
2. **`button-secondary`**: White `#FFFFFF`, black text, rounded pill, font-weight 480, border 1px solid `#E5E5E5` or borderless on color blocks, padding 8px 18px 10px.
3. **`top-nav`**: Sticky white bar, height 56px, monochrome links, right-anchored pill pair.
4. **`marquee-strip`**: Black ribbon directly under top-nav, height 36px, scrolling customer/status indicators in white uppercase mono.
5. **Color-Block Sections**: Full-width or container-width rounded `{rounded.lg}` (24px) panels in Lime, Lilac, Cream, Mint, Pink, Coral, and Navy with 48px interior padding and editorial typography.
6. **Pill Toggles**: Tab switchers using the pill shape (`rounded-full`), active state using black background with white text.
