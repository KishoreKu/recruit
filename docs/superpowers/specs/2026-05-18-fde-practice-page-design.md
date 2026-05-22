# Forward Deployed Engineers Practice Page — Design

**Date:** 2026-05-18
**Owner:** Kishore Kumar
**Status:** Design approved; implementation plan pending
**Target site:** westleyresource.com (existing static site on Firebase Hosting)

---

## 1. Context

Westley Resource is a recruiting firm. The company is launching a **Forward Deployed Engineers (FDE)** practice line: embedded engineers placed inside client teams to ship production AI/data work. The FDE bench is credentialed across six vendor partnerships and prepared for specific target-role archetypes such as the Palantir FDE pattern.

This design covers a single public marketing page that pitches the FDE practice to employer prospects. It is the first of several deliverables in the broader FDE program; other deliverables (candidate intake portal, internal ops dashboard, per-partner deep pages) are out of scope here and will be planned separately.

### Why this is needed now

- Westley was accepted into the Claude Partner Network. The immediate obligation is enrolling ten team members in Anthropic Academy. CCAF (Claude Certified Architect Foundations) unlocks for the organization once those ten complete the CPN learning path.
- Public announcement of the Claude Partner Network membership is currently **embargoed by Anthropic** pending portal launch. The page must be designed so the Anthropic block can flip from "in progress" to "announced partner" with a single content change, with no engineering work required.
- Westley already holds active partnerships with Microsoft, AWS, Google, Databricks, and Adobe. Those five are announceable today.
- The FDE practice is the commercial product that ties the partnerships together. The page exists to convert employer prospects into discovery calls.

---

## 2. Goals and non-goals

### Goals

- Pitch Westley's FDE practice to employer prospects in a single scrollable page.
- Showcase the six vendor partnerships and the FDE bench's credentials.
- Surface FDE specializations (initially the Palantir FDE archetype) cleanly separated from vendor partnerships, so no relationship is implied where none exists.
- Gate Anthropic-specific "partner" language until Anthropic clears public announcement; flip it on with a one-line data edit.
- Stay on the existing static-site stack (HTML, CSS, JS, Firebase Hosting). No new infrastructure. No backend.
- Be editable by non-engineers for the repeating content (partner blurbs, architect roster, FAQ, training tracks) without touching HTML or CSS.

### Non-goals (v1)

- Course delivery or LMS functionality. The CCAF course lives on Anthropic Academy; this page does not deliver lessons or quizzes.
- Candidate application flow ("Become a Westley FDE"). A small link to a future `/forward-deployed/apply` page is present but the apply page itself is out of scope.
- Internal ops dashboard for tracking the ten Academy enrollees. Out of scope.
- Per-partner deep pages (`/claude`, `/aws`, etc.). Out of scope; the data model is designed to permit them later without restructuring.
- Bringing up the FastAPI + Cloud Run + Cloud SQL backbone described in `VENTURE_ROADMAP.md`. Explicitly deferred. The page is static.
- Payments, accounts, authentication, certificate issuance.

---

## 3. Audience and positioning

**Primary audience:** Employer prospects evaluating whether to hire an embedded engineer for an AI/data engagement.

**Positioning sentence (canonical):** *Westley deploys Forward Deployed Engineers — embedded engineers who ship Claude/AI products inside your team. Our bench is certified across Anthropic, Microsoft, AWS, Google, Databricks, and Adobe, with specialization tracks including the Palantir FDE archetype.*

**Primary CTA:** "Book a 30-min FDE discovery call" → `/contact.html?topic=fde`. Reuses the existing contact page; the query param routes the lead for tracking.

**Secondary CTA (small, page footer):** "Are you an engineer? Apply to the bench →" links to `/forward-deployed/apply` (stub page out of scope for v1; link is a placeholder).

### Two-bucket model (critical)

The page treats partnerships and training tracks as **distinct categories**, never conflated:

- **Partnerships (6):** Anthropic (announcement pending), Microsoft, AWS, Google, Databricks, Adobe. These are formal vendor relationships. Renders include partner logos and, when announceable, partner badges and "member" language.
- **Training tracks (1+):** Palantir Forward Deployed Engineer is the first. These are role archetypes Westley trains candidates against, independent of any vendor relationship. Renders explicitly disclaim that Westley is not a partner of the target employer.

The data model enforces this separation via two top-level arrays (`partnerships[]`, `training_tracks[]`), and the page renders them in visually distinct sections.

---

## 4. Page structure

URL: `/forward-deployed` (clean URL via Firebase Hosting rewrite). File: `forward-deployed.html`. Nav label: **"FDE Practice"** (chosen to keep the existing nav row balanced; the full name "Forward Deployed Engineers" appears in the hero, the page title, and meta description).

Single long-scroll page, nine blocks in order:

1. **Hero.** Headline, one-line subhead, primary CTA. Background visual on-brand with existing site.
2. **What an FDE does.** Four mini-cards: *Embed*, *Build*, *Transfer*, *Certify*. Quick-read value proof.
3. **Partnerships strip.** Six partner logos in a single horizontal row, equal visual weight. Each renders its `blurb_announceable` or `blurb_pre_announce` based on the per-partner `announceable` flag. No partner gets featured treatment over another.
4. **Certifications block.** Short explainer for the cert ecosystem (CCAF and equivalents), with a compact cert-badge legend keyed off `data.certifications[]`.
5. **Certified architects roster.** Card per FDE: photo, name, role, cert badges, LinkedIn. Cert badges resolve from each architect's `cert_ids[]` against the shared `certifications[]` lookup. Architects with `in_training: true` render a muted badge and an "in training" pill so the section can ship before the ten Academy enrollees complete.
6. **FDE specializations we train for.** Visually distinct block. First entry: Palantir Forward Deployed Engineer. Each track shows: target role/employer, archetype description, curriculum summary, "N candidates currently training" / "N ready," and an explicit non-partnership disclaimer.
7. **Engagement models.** Three cards: *Staff augmentation*, *Fixed-scope project*, *Direct-hire placement*. Each card: timeline, brief description, "good fit" signal. Reflects Westley's hybrid (W2 + contractor + placement) model.
8. **FAQ.** Six to eight items addressing the actual questions employer prospects ask: pricing model, time to first FDE on-site, NDA & IP, exit/transition, geographic coverage, vetting process, mismatch handling, trial options. Rendered with native `<details>` / `<summary>` for accessibility.
9. **Final CTA.** Primary CTA repeated. Secondary "Apply to the bench" link.

**Cross-cutting:**

- Sticky in-page sub-nav at the top of the page (Hero / Partnerships / Roster / Specializations / Engagement / FAQ) using anchor links. Collapses to a dropdown on mobile.
- Mobile-first. Multi-card rows collapse to single column. Roster grid: 3 / 2 / 1 columns by breakpoint.

---

## 5. Data model

All repeating content and per-partner blurbs live in a single JSON file. Static structural copy (hero, section headings) stays in HTML for SEO and no-JS fallback (see §6).

**File:** `data/fde-practice.json`

```jsonc
{
  "feature_flags": {
    "partnerships_strip_visible": true,
    "roster_visible": true,
    "specializations_visible": true
  },

  "partnerships": [
    {
      "id": "anthropic",
      "name": "Anthropic",
      "logo": "assets/partners/anthropic.svg",
      "blurb_announceable": "Claude Partner Network member. Our architects hold CCAF.",
      "blurb_pre_announce": "Our team trains through Anthropic Academy and is on the path to CCAF certification.",
      "announceable": false
    },
    { "id": "microsoft",  "name": "Microsoft",       "logo": "assets/partners/microsoft.svg",  "blurb_announceable": "...", "announceable": true },
    { "id": "aws",        "name": "AWS",             "logo": "assets/partners/aws.svg",        "blurb_announceable": "...", "announceable": true },
    { "id": "google",     "name": "Google Cloud",    "logo": "assets/partners/google.svg",     "blurb_announceable": "...", "announceable": true },
    { "id": "databricks", "name": "Databricks",      "logo": "assets/partners/databricks.svg", "blurb_announceable": "...", "announceable": true },
    { "id": "adobe",      "name": "Adobe",           "logo": "assets/partners/adobe.svg",      "blurb_announceable": "...", "announceable": true }
  ],

  "training_tracks": [
    {
      "id": "palantir-fde",
      "name": "Palantir Forward Deployed Engineer",
      "target_employer": "Palantir",
      "logo": "assets/tracks/palantir.svg",
      "blurb": "We train candidates against the Palantir FDE archetype: ontology design, Foundry/AIP fluency, customer-first delivery.",
      "curriculum": ["Ontology design fundamentals", "Foundry & AIP hands-on", "Customer-embedded delivery practices"],
      "candidates_training": 0,
      "candidates_ready": 0,
      "disclaimer": "Westley is not a Palantir partner. This track prepares candidates for the Palantir FDE role pattern."
    }
  ],

  "certifications": [
    { "id": "ccaf",       "name": "Claude Certified Architect Foundations", "issuer": "Anthropic", "badge": "assets/certs/ccaf.svg",       "blurb": "..." },
    { "id": "aws-sa-pro", "name": "AWS Solutions Architect Pro",            "issuer": "AWS",       "badge": "assets/certs/aws-sa-pro.svg", "blurb": "..." }
  ],

  "architects": [
    {
      "name": "TBD",
      "role": "Senior FDE",
      "photo": "assets/team/placeholder.svg",
      "cert_ids": ["ccaf"],
      "linkedin": "https://www.linkedin.com/in/...",
      "in_training": true
    }
  ],

  "what_fde_does": [
    { "icon": "embed",    "title": "Embed",    "body": "..." },
    { "icon": "build",    "title": "Build",    "body": "..." },
    { "icon": "transfer", "title": "Transfer", "body": "..." },
    { "icon": "certify",  "title": "Certify",  "body": "..." }
  ],

  "engagement_models": [
    { "id": "staff-aug",   "title": "Staff augmentation",    "timeline": "1–6 months", "body": "...", "fit": "..." },
    { "id": "fixed-scope", "title": "Fixed-scope project",   "timeline": "4–12 weeks", "body": "...", "fit": "..." },
    { "id": "direct-hire", "title": "Direct-hire placement", "timeline": "30–60 days", "body": "...", "fit": "..." }
  ],

  "faq": [
    { "q": "How quickly can you put an FDE on-site?", "a": "..." }
  ]
}
```

**Schema doc:** `data/fde-practice.schema.md` documents every field in plain English so non-engineers can edit confidently.

**Optional CI guard:** `data/fde-practice.schema.json` plus a GitHub Action that validates the data file on every push. Catches typos and missing required fields pre-deploy. Recommended but not blocking for v1.

### Gating rules (the renderer enforces these)

1. **Per-partner `announceable` flag.** When `false`: render logo + `blurb_pre_announce`, omit any "partner" / "member" language, no badge. When `true`: render `blurb_announceable` and the official partner badge.
2. **Per-architect `in_training` flag.** When `true`: muted cert badge + "in training" pill. When `false`: full-color badge.
3. **Section-level `feature_flags`.** Each visibility flag, when `false`, hides the entire section (header included).

### Defensive rendering

If any field referenced by a renderer is missing or malformed, the renderer skips that record (or section) rather than throwing. A console warning fires. A half-filled JSON produces a thinner page, never a broken one.

---

## 6. Rendering architecture

### File layout (new and modified)

```
forward-deployed.html               new
data/fde-practice.json              new
data/fde-practice.schema.md         new
data/fde-practice.schema.json       new (optional CI guard)
assets/partners/*.svg               new (6 logos)
assets/tracks/palantir.svg          new
assets/certs/*.svg                  new (per cert in the bank)
assets/team/placeholder.svg         new
assets/team/*.{jpg,webp}            new (architect photos as they come in)
js/fde-practice.js                  new (~250 LOC est.)
styles.css                          modified (new section styles)
firebase.json                       modified (clean-URL rewrite)
index.html, about.html, services.html, employers.html, candidates.html, contact.html
                                    modified (each file has its own copy of the nav;
                                              the "FDE Practice" link is added to all six,
                                              plus to forward-deployed.html itself)
```

### What stays in HTML vs JSON

This split is deliberate, for SEO and no-JS resilience:

- **HTML (`forward-deployed.html`):** `<title>`, meta description, hero headline + subhead + primary CTA, every section heading string, FAQ section heading, footer. These are static structural strings that should be indexable by Google on first crawl and visible if JS fails.
- **JSON (`data/fde-practice.json`):** every repeating record (partners, architects, tracks, certs, FAQ entries, engagement models, "what an FDE does" cards), plus per-partner blurbs and announceability flags.

Trade-off: editing the hero requires touching HTML. Acceptable — the hero changes rarely.

### Page lifecycle

1. Browser loads `forward-deployed.html`. Static hero, section headings, sub-nav, and CTA render immediately. No spinner needed for above-the-fold view.
2. An inline `<script type="module">` calls `initFdePractice()` from `js/fde-practice.js`.
3. JS fetches `data/fde-practice.json`. The existing site has no build step, so cache control is handled by `firebase.json` headers: `Cache-Control: public, max-age=300` on the JSON file (5-minute browser cache, edge-revalidated). This makes a content edit visible within 5 minutes of deploy without requiring a deploy-time hash injection. If sub-5-minute propagation ever matters, we can switch to a `?v=<git-sha>` query string injected via a small `pre-deploy` script later.
4. On fetch success, each per-section renderer runs against its slice of the data. Renderers run in DOM order but do not await one another.
5. On fetch failure (network, 404, invalid JSON), every dynamic section silently absents itself. The static hero, section headings, sub-nav, and CTA remain. A console warning fires; no visible error.

### Module structure

`js/fde-practice.js` exports one entry point. Internally, one small renderer per section:

```
initFdePractice()
├─ renderPartnerships(data.partnerships, mount)
├─ renderTrainingTracks(data.training_tracks, mount)
├─ renderCertifications(data.certifications, mount)
├─ renderArchitects(data.architects, data.certifications, mount)
├─ renderWhatFdeDoes(data.what_fde_does, mount)
├─ renderEngagementModels(data.engagement_models, mount)
└─ renderFaq(data.faq, mount)
```

Each renderer:

- Takes its data slice and a DOM mount element.
- Mutates the DOM via template-string helpers. No framework.
- Returns void.
- Is independently testable (data-in, DOM-out).
- Skips silently if its data slice is missing or empty.

`renderArchitects` receives `certifications` so cert badges resolve from each architect's `cert_ids[]` without duplicating badge metadata across architects.

### Error handling rules

- Missing fields on a record → skip that record, console-warn, continue.
- Empty array for a section → hide the entire section, including its heading.
- Failed fetch → all dynamic sections silently absent.
- Invalid JSON → same as failed fetch.

These rules apply uniformly across renderers.

---

## 7. Accessibility

- Semantic landmarks: `<header>`, `<main>`, `<section aria-labelledby="...">`, `<nav>` for the sub-nav.
- All architect, cert badge, partner logo, and track logo images have descriptive `alt` text generated from data (e.g., `alt="${cert.name} badge"`).
- Sub-nav: real `<a href="#section-id">` links, keyboard-navigable, with visible focus styles inherited from the existing site.
- FAQ: native `<details>` / `<summary>` for expand/collapse. No JS required; keyboard accessible by default.
- Color contrast on cert badges: verify ≥4.5:1 against the surface they sit on.

---

## 8. SEO

- `<title>` and meta description target "Forward Deployed Engineers" and "hire Claude/AI engineer" intent.
- Hero copy is in initial HTML so first-crawl indexing is reliable.
- Open Graph and Twitter Card meta tags included for share previews.
- Schema.org `ProfessionalService` JSON-LD on the page (optional, recommended).
- The partnerships strip is the page's strongest credibility signal; partner names appear in the JSON-rendered DOM, which Google does crawl but with lag. Partner names also appear in the page copy in HTML where natural, so SEO does not depend on JS rendering for partner attribution.

---

## 9. Embargo and announcement workflow

When Anthropic clears public announcement of the Claude Partner Network membership:

1. Edit `data/fde-practice.json`. Change `partnerships[0].announceable` from `false` to `true`.
2. Commit and deploy. No code change.
3. The page now renders the official "Claude Partner Network member" badge and `blurb_announceable` copy for Anthropic.

Until that moment:

- The page contains no "Claude Partner Network" wording, no "partner" language about Anthropic, and no Anthropic partner badge.
- The Anthropic block renders `blurb_pre_announce` text: "Our team trains through Anthropic Academy and is on the path to CCAF certification." This is factually accurate and pre-announcement-safe.

---

## 10. Performance budget

- `data/fde-practice.json`: target <50 KB. Realistic landing size ~8–15 KB.
- `js/fde-practice.js`: target <10 KB minified.
- Partner / track / cert SVGs: optimized via SVGO. Aim for <3 KB each.
- Architect photos: `loading="lazy"`, served at 2× resolution, ≤200 KB each.
- No new third-party scripts. Google Analytics (already on the site) is the only off-domain script.

---

## 11. Testing and verification

No formal test framework on this site. Verification is a manual smoke checklist run before each deploy, plus one optional automated guard.

**Pre-deploy manual smoke:**

- Load `/forward-deployed`. Scroll the full page on desktop. Confirm all nine sections render with expected content.
- DevTools network throttling: simulate `fde-practice.json` failure (404 or network error). Confirm: static hero, section headings, sub-nav, and primary CTA still render. Dynamic sections absent. Console warning visible; no red errors.
- Edit `data/fde-practice.json` locally. Flip `partnerships[0].announceable` from `false` to `true`. Reload. Confirm Anthropic block shows the announceable blurb and the partner badge appears. Revert before deploy.
- Mobile viewport (375 px width). Confirm sub-nav collapses to a dropdown, multi-card rows reflow to single column, roster grid reflows to one column.
- Keyboard-only navigation: tab through the sub-nav and through the FAQ. Confirm focus visible on every interactive element. Expand a FAQ item with Enter.

**Optional automated guard (recommended):**

- `data/fde-practice.schema.json` defines the required shape.
- GitHub Action runs `ajv validate` on every push to `main` and on every pull request. Fails the build on missing required fields or invalid types. ~30 min to set up.

---

## 12. Browser support

Matches existing site: latest Chrome, Firefox, Safari, Edge, plus iOS Safari and Chrome Mobile. The renderer uses `fetch`, ES modules, and template literals — all 99%+ supported. No transpilation.

---

## 13. Out-of-scope, deferred items

The following are explicitly not part of this design and will be planned separately if and when they become priorities:

- Candidate intake / application portal (`/forward-deployed/apply` is a stub).
- Internal ops dashboard for tracking Anthropic Academy progress for the ten enrollees.
- Per-partner deep pages (`/claude`, `/microsoft`, etc.). The data model is designed to enable these later by extending the partnership records with `detail_page_slug`-style fields.
- `/partnerships` hub page. Same.
- FastAPI / Cloud Run / Cloud SQL backbone from `VENTURE_ROADMAP.md`. Deferred until a workload requires it.
- Payment, accounts, certificate issuance, course delivery. The course lives on Anthropic Academy.

---

## 14. Decisions log (for traceability)

- **Course delivery is out of scope.** The CCAF course lives on Anthropic Academy. Westley's surface area is positioning and recruiting around it.
- **v1 audience is employer prospects.** Candidate intake is deferred.
- **Hybrid engagement model.** The page advertises staff augmentation, fixed-scope project, and direct-hire placement.
- **Static site, no backend.** Defer FastAPI. Roster and content edits happen via JSON in repo.
- **Two buckets, never conflated.** Partnerships ≠ training tracks. Palantir lives in training tracks with an explicit non-partnership disclaimer.
- **Hero stays in HTML.** SEO and no-JS fallback override the "all content in JSON" preference.
- **Anthropic announcement gated by a single per-partner flag.** No engineering change required to flip.
