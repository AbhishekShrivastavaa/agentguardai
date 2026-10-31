---
name: emil-design-eng
description: "Apply design-engineering judgment to frontend work: refine interaction details, component behavior, and purposeful motion. Use when building or polishing UI interactions and animations."
---

# Design Engineering

Use this skill to make interfaces feel deliberate and responsive without adding motion or decoration for its own sake. Treat this as workspace guidance, not an official publication or endorsement by Emil Kowalski.

## Workflow

1. Inspect the existing component, styles, and nearby UI before editing. Reuse the project's established patterns and dependencies.
2. Identify the interaction's purpose and states: idle, hover, focus, pressed, loading, success, and error where relevant.
3. Make feedback immediate and clear. Prefer small, purposeful transitions and natural easing over large, attention-seeking movement.
4. Keep motion interruptible and consistent with the user's action. Avoid animating layout properties when a transform or opacity transition is sufficient.
5. Respect `prefers-reduced-motion`; preserve a clear non-animated state and never make motion necessary to understand or use a control.
6. Verify keyboard focus, touch behavior, responsive layout, and the final visual result at relevant viewport sizes.

## Quality checks

- Every interactive control communicates its state and remains usable by keyboard and touch.
- Timing and easing support the action rather than delaying it.
- Motion does not obscure content, cause unexpected layout shifts, or run indefinitely without user benefit.
- Existing functionality and visual conventions remain intact.
