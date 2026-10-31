---
name: impeccable
description: "Audit and polish frontend interfaces for visual quality, consistency, accessibility, and responsive behavior. Use when asked to critique, refine, or finish an existing UI."
---

# Impeccable UI Review

Improve the interface that exists, fixing its highest-impact quality problems before making cosmetic changes. Keep the requested scope and the product's established design language.

## Review workflow

1. Inspect the relevant page, shared styles, and component patterns. Run the existing frontend checks when practical.
2. Review the page in this order:
   - Content hierarchy and clarity of the primary action
   - Layout, alignment, spacing, and responsive behavior
   - Typography, contrast, and consistency of colors and surfaces
   - Interactive states, keyboard use, focus visibility, and error feedback
   - Motion, loading states, and small visual details
3. Identify the few issues with the greatest effect on usability or polish. Fix those first; do not produce a long list of speculative nits.
4. Make focused changes using existing tokens and components. Avoid introducing a new dependency or design system for a local polish task.
5. Recheck the affected states and viewport sizes, then run the narrowest relevant build or test.

## Review standards

- Preserve functionality and content unless the user asks to change them.
- Do not hide a usability issue with decoration or solve a local inconsistency by adding another one-off style.
- Check color contrast, semantic controls, keyboard navigation, and reduced-motion behavior.
- Report any visual state that could not be verified rather than claiming it was tested.
