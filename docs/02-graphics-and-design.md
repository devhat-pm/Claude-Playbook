# Graphics, design & visuals

Claude doesn't generate raster images the way an image model does. It *draws* — SVG, HTML/CSS, canvas, charts from data, and full design canvases — and that turns out to cover most of what people actually need.

## What you can ask for

| Need | Ask | What happens |
|---|---|---|
| Quick explainer visual in chat | "show me a diagram of how OAuth works" | Inline SVG/HTML, rendered in the reply |
| Chart of data | attach the CSV, "chart revenue by month" | Claude loads the data in code, plots it; dashboards go to a Dashboard artifact |
| App screens / landing page / poster / flyer / menu / business card | "mock up the onboarding flow", "design a flyer for…" | **Design** artifact on a canvas you can edit, compare versions, export PDF/PNG |
| Slides | "make a deck on…" | **Slides** artifact; export PPTX/PDF |
| Interactive widget | "build a mortgage calculator I can play with" | HTML artifact or inline interactive |
| Flowchart / architecture / brainstorm | "whiteboard the system" | **Whiteboard** artifact (movable boxes & stickies). Artifact type; availability varies by account, no public docs yet |
| Short animation | "a 10-second animated logo reveal" | **Motion** artifact |
| Brand kit | "set up a design system from our site" | **Design System** artifact, reused by every later deck/design |

## Claude Design

- Chat on the left, canvas on the right. Describe, review, say what to change. It asks clarifying questions when needed.
- Feed it a **design system**: colours, type, components. Teams: set this up *first* or you get generic output. It can build one by reading your codebase or design files.
- Hand-off to **Claude Code** (`/design` and `/design-sync` keep them in sync) — design → working components.
- Exports: HTML bundle, PPTX, PDF, images; Google Slides from the standalone version.
- Ask it to **review** its own design: accessibility, contrast ratios, hierarchy, usability.
- Works in small increments: structure → content → polish. Don't try to one-shot a whole app.
- Counts against your normal usage pool.
- Docs: https://support.claude.com/en/articles/14604416

## Getting non-generic output

Models drift toward the "AI slop" aesthetic unless told otherwise. The official frontend-design skill prompt fixes most of it; paraphrased:

- Distinctive typography — not Inter/Roboto/Arial/system fonts, and not the same "safe" alternatives every time.
- Commit to a palette; dominant colour + sharp accent beats timid evenly-spread colours. Use CSS variables.
- One orchestrated page-load animation with staggered reveals > scattered micro-interactions.
- Backgrounds with depth (layered gradients, patterns) rather than flat white.
- Avoid purple-gradient-on-white and predictable card grids.

Paste the full skill into any UI prompt: https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md

## Limits to know up front

- Claude **won't draw known characters, logos, album covers, or brand mascots**, and won't "get closer" to one by swapping elements. It will invent an original. Public-domain works and *your own* logo are fine.
- Inline visuals never depict real identifiable people, gore, or licensed media.
- For photographic/raster image generation, use an image-generation connector (several are in the connector directory) — Claude will orchestrate it.

## Lesser-known

- "Compare X vs Y" or "how does X work" often gets a *proactive* diagram without you asking — if you'd rather have prose, say so.
- A Mermaid/DOT/SVG source you paste can be published as a rendered artifact page.
- Dashboards can hold live data: Claude updates the rows later without regenerating the page.
- Artifacts work in light *and* dark mode; ask Claude to check both if it matters.
- Mobile: charts of your health data, maps with pins, itineraries with routes and recipe cards all render as native cards.
