# Forward Deployed Engineers Practice Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a single public marketing page at `/forward-deployed` that pitches Westley's Forward Deployed Engineers practice to employer prospects, surfaces six vendor partnerships (with the Anthropic block gated until Anthropic clears public announcement), and surfaces FDE specialization tracks (initially Palantir FDE) explicitly distinct from vendor partnerships.

**Architecture:** Static HTML page on the existing Firebase Hosting stack. Static structural copy (hero, section headings) lives in `forward-deployed.html`. All repeating content (partner blurbs, architect roster, certifications, training tracks, engagement models, FAQ) lives in `data/fde-practice.json` and is rendered at page load by `js/fde-practice.js`. Per-partner `announceable` flags and per-architect `in_training` flags drive content gating. Defensive renderers skip missing fields/sections silently so a malformed JSON file never produces a broken page.

**Tech Stack:** HTML5, vanilla CSS (extending existing `styles.css` design tokens), ES modules in vanilla JS, Firebase Hosting. No frameworks, no build step, no backend.

**Reference spec:** `docs/superpowers/specs/2026-05-18-fde-practice-page-design.md`

---

## File Structure

**Files to create:**
- `forward-deployed.html` — page shell with static hero, section headings, mount points
- `data/fde-practice.json` — repeating content + gating flags
- `data/fde-practice.schema.md` — plain-English field reference for editors
- `js/fde-practice.js` — single ES module with one renderer per section
- `assets/partners/anthropic.svg`, `microsoft.svg`, `aws.svg`, `google.svg`, `databricks.svg`, `adobe.svg` — partner logos (placeholders in v1, swap with official brand-kit assets later)
- `assets/tracks/palantir.svg` — Palantir track logo (text-only placeholder, never branded as partnership)
- `assets/certs/ccaf.svg`, `aws-sa-pro.svg`, `azure-sa.svg`, `gcp-pca.svg`, `databricks-de.svg` — cert badge placeholders
- `assets/team/placeholder.svg` — neutral silhouette for architects without published photos

**Files to modify:**
- `styles.css` — appended FDE section styles (no edits to existing rules)
- `firebase.json` — add a short `Cache-Control` rule for `data/*.json`
- `index.html`, `about.html`, `services.html`, `employers.html`, `candidates.html`, `contact.html` — one nav link added to each (between "Services" and "For Employers")

**Files NOT touched:**
- `script.js` (existing site JS) — FDE module is independent
- Any existing HTML inside non-nav sections of the six pages
- Existing CSS rules

---

## Conventions

- **Commits:** one commit per task, conventional-commit style (`feat:`, `chore:`, `style:`, `docs:`).
- **Verification:** the site has no test framework. Each task ends with concrete manual verification steps (commands to run, what to observe). When fixing rendering bugs, re-run that task's verification block.
- **Local preview:** the engineer can run `python3 -m http.server 8000` from the repo root, then visit `http://localhost:8000/forward-deployed.html`. (Firebase Hosting clean URLs only resolve via `firebase serve` or in production; the `.html` extension works locally with plain HTTP servers.)
- **Design tokens:** new CSS uses existing custom properties from `styles.css:13–45` (`--primary-color`, `--text-dark`, `--text-muted`, `--gradient-primary`, etc.). No new color literals.

---

## Task 1: Create page shell with static structural copy

**Files:**
- Create: `forward-deployed.html`

- [ ] **Step 1: Write the full `forward-deployed.html` shell**

This contains every static string from the spec: title, meta, hero, sub-nav, all nine section headings, mount points for dynamic content, FAQ heading, footer, and the inline `<script type="module">` that calls `initFdePractice`. Dynamic mounts are empty `<div>`s with stable ids.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Forward Deployed Engineers | Westley Resource</title>
  <meta name="description" content="Hire Forward Deployed Engineers from Westley Resource. Embedded engineers who ship Claude/AI products inside your team, certified across Anthropic, Microsoft, AWS, Google, Databricks, and Adobe.">

  <!-- Open Graph -->
  <meta property="og:title" content="Forward Deployed Engineers | Westley Resource">
  <meta property="og:description" content="Embedded engineers who ship Claude/AI products inside your team. Certified across six vendor ecosystems.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://westleyresource.com/forward-deployed">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="styles.css">

  <!-- Favicon (reuse existing) -->
  <link rel="icon" type="image/png" href="assets/images/logo-symbol.png">
</head>
<body>

  <!-- Navigation (FDE Practice link is added in Task 2; this file's nav mirrors that final state) -->
  <nav class="navbar">
    <div class="nav-container">
      <a href="index.html" class="logo-container">
        <img src="assets/images/logo-symbol.png" alt="Westley Resource Icon" class="logo-icon">
        <div class="logo-text">
          <div class="logo-title">
            <span class="logo-title-first">WESTLEY</span>
          </div>
        </div>
      </a>

      <button class="nav-toggle" aria-label="Toggle navigation">
        <span></span><span></span><span></span>
      </button>

      <ul class="nav-menu">
        <li><a href="index.html" class="nav-link">Home</a></li>
        <li><a href="about.html" class="nav-link">About</a></li>
        <li><a href="services.html" class="nav-link">Services</a></li>
        <li><a href="forward-deployed.html" class="nav-link nav-link-active">FDE Practice</a></li>
        <li><a href="employers.html" class="nav-link">For Employers</a></li>
        <li><a href="candidates.html" class="nav-link">For Candidates</a></li>
        <li><a href="contact.html" class="nav-link"><span class="btn btn-primary">Contact Us</span></a></li>
      </ul>
    </div>
  </nav>

  <!-- Hero -->
  <section class="hero fde-hero" id="hero">
    <div class="container">
      <div class="hero-content">
        <h1>Forward Deployed Engineers, ready to ship inside your team</h1>
        <p>Embedded, certified engineers backed by partnerships with Anthropic, Microsoft, AWS, Google, Databricks, and Adobe. Hire by the engagement, by the project, or as a direct placement.</p>
        <div class="hero-buttons">
          <a href="contact.html?topic=fde" class="btn btn-primary btn-lg">Book a 30-min discovery call</a>
          <a href="#partnerships" class="btn btn-secondary btn-lg">See our credentials</a>
        </div>
      </div>
    </div>
  </section>

  <!-- Sticky in-page sub-nav (styles + behavior added in Task 13) -->
  <nav class="fde-subnav" aria-label="Page sections">
    <div class="container">
      <ul>
        <li><a href="#what-fde-does">What an FDE does</a></li>
        <li><a href="#partnerships">Partnerships</a></li>
        <li><a href="#roster">Bench</a></li>
        <li><a href="#specializations">Specializations</a></li>
        <li><a href="#engagement">Engagement</a></li>
        <li><a href="#faq">FAQ</a></li>
      </ul>
    </div>
  </nav>

  <main>
    <!-- What an FDE does -->
    <section class="section fde-section" id="what-fde-does" aria-labelledby="what-fde-does-heading">
      <div class="container">
        <h2 id="what-fde-does-heading" class="section-heading">What an FDE does</h2>
        <div id="what-fde-does-mount" class="fde-grid"></div>
      </div>
    </section>

    <!-- Partnerships -->
    <section class="section fde-section" id="partnerships" aria-labelledby="partnerships-heading">
      <div class="container">
        <h2 id="partnerships-heading" class="section-heading">Our partnerships</h2>
        <p class="section-lead">We hold active partnerships with these vendors. Each one represents a formal relationship, joint training, and accountable certification paths.</p>
        <div id="partnerships-mount" class="fde-partners-strip"></div>
      </div>
    </section>

    <!-- Certifications legend -->
    <section class="section fde-section" id="certifications" aria-labelledby="certifications-heading">
      <div class="container">
        <h2 id="certifications-heading" class="section-heading">The certifications backing our bench</h2>
        <p class="section-lead">Hiring a credentialed engineer de-risks the engagement. These are the certs our FDEs carry.</p>
        <div id="certifications-mount" class="fde-cert-legend"></div>
      </div>
    </section>

    <!-- Roster -->
    <section class="section fde-section" id="roster" aria-labelledby="roster-heading">
      <div class="container">
        <h2 id="roster-heading" class="section-heading">Our bench</h2>
        <p class="section-lead">Engineers actively training, certified, or available for engagement.</p>
        <div id="roster-mount" class="fde-roster"></div>
      </div>
    </section>

    <!-- Training tracks -->
    <section class="section fde-section" id="specializations" aria-labelledby="specializations-heading">
      <div class="container">
        <h2 id="specializations-heading" class="section-heading">FDE specializations we train for</h2>
        <p class="section-lead">Role archetypes our candidates prepare for, independent of any vendor partnership.</p>
        <div id="tracks-mount" class="fde-tracks"></div>
      </div>
    </section>

    <!-- Engagement models -->
    <section class="section fde-section" id="engagement" aria-labelledby="engagement-heading">
      <div class="container">
        <h2 id="engagement-heading" class="section-heading">How to engage</h2>
        <div id="engagement-mount" class="fde-grid"></div>
      </div>
    </section>

    <!-- FAQ -->
    <section class="section fde-section" id="faq" aria-labelledby="faq-heading">
      <div class="container">
        <h2 id="faq-heading" class="section-heading">Frequently asked questions</h2>
        <div id="faq-mount" class="fde-faq"></div>
      </div>
    </section>

    <!-- Final CTA -->
    <section class="section fde-section fde-final-cta" aria-labelledby="final-cta-heading">
      <div class="container text-center">
        <h2 id="final-cta-heading" class="section-heading">Ready to embed an FDE?</h2>
        <p>Book a 30-minute call and we'll walk you through the bench, the engagement options, and a realistic timeline.</p>
        <a href="contact.html?topic=fde" class="btn btn-primary btn-lg">Book a 30-min discovery call</a>
        <p class="fde-secondary-cta">Are you an engineer? <a href="forward-deployed/apply.html">Apply to the bench &rarr;</a></p>
      </div>
    </section>
  </main>

  <!-- Footer (matches existing site footer; abbreviated for brevity — copy verbatim from index.html in Task 1) -->
  <footer class="footer">
    <div class="container">
      <p>&copy; 2026 Westley Resource. All rights reserved.</p>
    </div>
  </footer>

  <!-- Existing site interactivity (mobile nav toggle, etc.) -->
  <script src="script.js"></script>

  <!-- FDE Practice renderer (created in Task 5) -->
  <script type="module">
    import { initFdePractice } from './js/fde-practice.js';
    initFdePractice();
  </script>
</body>
</html>
```

**Important:** Before saving, copy the actual `<footer>` block from `index.html` (lines roughly 250–end — locate the existing `<footer class="footer">` and paste verbatim) so the FDE page footer matches every other page exactly. The placeholder footer above is a stub. Do the same for the Google Analytics snippet if `index.html` carries one in `<head>` — copy that verbatim into the FDE page `<head>` for consistent tracking.

- [ ] **Step 2: Verify the page loads locally**

Run from the repo root:
```bash
python3 -m http.server 8000
```

Then open `http://localhost:8000/forward-deployed.html` in a browser.

Expected: the page loads with the hero ("Forward Deployed Engineers, ready to ship inside your team"), the sub-nav row, every section heading visible in order, the final CTA, and the footer. The dynamic sections appear as empty space below their headings — that's correct for now. The browser console shows a 404 for `./js/fde-practice.js` — also expected (created in Task 5).

Stop the server with `Ctrl+C`.

- [ ] **Step 3: Commit**

```bash
git add forward-deployed.html
git commit -m "feat: scaffold Forward Deployed Engineers page shell

Static structural copy (hero, section headings, sub-nav, FAQ heading, final CTA)
in HTML for SEO and no-JS fallback. Dynamic mount points are empty divs to be
populated by js/fde-practice.js once the renderer ships (Task 5)."
```

---

## Task 2: Add "FDE Practice" link to nav across all six existing pages

**Files:**
- Modify: `index.html`, `about.html`, `services.html`, `employers.html`, `candidates.html`, `contact.html`

The existing nav in each file is identical in structure (see `index.html:30–62`). The new link goes between the "Services" `<li>` and the "For Employers" `<li>`.

- [ ] **Step 1: Add nav link to `index.html`**

Find this block (around line 51–57):
```html
        <li><a href="services.html" class="nav-link">Services</a></li>
        <li><a href="employers.html" class="nav-link">For Employers</a></li>
```

Replace with:
```html
        <li><a href="services.html" class="nav-link">Services</a></li>
        <li><a href="forward-deployed.html" class="nav-link">FDE Practice</a></li>
        <li><a href="employers.html" class="nav-link">For Employers</a></li>
```

- [ ] **Step 2: Repeat the same edit in the other five pages**

Apply the identical edit to `about.html`, `services.html`, `employers.html`, `candidates.html`, `contact.html`. The before/after lines are the same in every file.

- [ ] **Step 3: Verify the nav link appears on every page**

Run `python3 -m http.server 8000` from repo root. Visit each of:
- `http://localhost:8000/index.html`
- `http://localhost:8000/about.html`
- `http://localhost:8000/services.html`
- `http://localhost:8000/employers.html`
- `http://localhost:8000/candidates.html`
- `http://localhost:8000/contact.html`

Expected on every page: the nav menu shows "FDE Practice" between "Services" and "For Employers." Clicking it lands on `forward-deployed.html`.

Also verify on `http://localhost:8000/forward-deployed.html` that the FDE Practice link in its own nav carries the `nav-link-active` class (already set in Task 1's HTML).

- [ ] **Step 4: Commit**

```bash
git add index.html about.html services.html employers.html candidates.html contact.html
git commit -m "feat: add FDE Practice nav link to all six existing pages

Position: between Services and For Employers. Each page's nav has its own
copy; this commit edits all six identically."
```

---

## Task 3: Create placeholder SVG assets

The page references twelve SVG assets in `data/fde-practice.json` (Task 4). For v1 we ship neutral text-based placeholders. Sourcing official brand-kit logos is a follow-on task — partner logos have legal usage requirements that the page-rendering work shouldn't block on.

**Files:**
- Create: `assets/partners/anthropic.svg`, `microsoft.svg`, `aws.svg`, `google.svg`, `databricks.svg`, `adobe.svg`
- Create: `assets/tracks/palantir.svg`
- Create: `assets/certs/ccaf.svg`, `aws-sa-pro.svg`, `azure-sa.svg`, `gcp-pca.svg`, `databricks-de.svg`
- Create: `assets/team/placeholder.svg`

- [ ] **Step 1: Create the partner-logo placeholder SVGs**

All six partner SVGs share an identical structure — only the visible label changes. Template:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 80" role="img" aria-label="LABEL logo placeholder">
  <rect width="200" height="80" rx="8" fill="#f3f5f8"/>
  <text x="100" y="48" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="20" font-weight="600" fill="#1f2937">LABEL</text>
</svg>
```

Create six files. Substitute `LABEL` with the partner name in each:
- `assets/partners/anthropic.svg` → `Anthropic`
- `assets/partners/microsoft.svg` → `Microsoft`
- `assets/partners/aws.svg` → `AWS`
- `assets/partners/google.svg` → `Google Cloud`
- `assets/partners/databricks.svg` → `Databricks`
- `assets/partners/adobe.svg` → `Adobe`

- [ ] **Step 2: Create the Palantir training-track logo**

Visually distinct from the partner logos — different aspect ratio, accent border — so a reader cannot confuse it for a partner badge.

`assets/tracks/palantir.svg`:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 80" role="img" aria-label="Palantir FDE training track">
  <rect width="240" height="80" rx="8" fill="#fff" stroke="#c0392b" stroke-width="2" stroke-dasharray="6 4"/>
  <text x="120" y="34" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="600" fill="#1f2937">Training track</text>
  <text x="120" y="58" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="18" font-weight="700" fill="#c0392b">Palantir FDE</text>
</svg>
```

- [ ] **Step 3: Create the cert-badge placeholders**

Shared template — a 120×120 rounded square with the cert short-code.

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="CERT_NAME badge placeholder">
  <rect width="120" height="120" rx="16" fill="#1f3a8a"/>
  <text x="60" y="68" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="22" font-weight="700" fill="#fff">CERT_CODE</text>
</svg>
```

Create five cert badges:
- `assets/certs/ccaf.svg` → `CERT_CODE = CCAF`, `CERT_NAME = Claude Certified Architect Foundations`
- `assets/certs/aws-sa-pro.svg` → `CERT_CODE = AWS SAP`, `CERT_NAME = AWS Solutions Architect Pro`
- `assets/certs/azure-sa.svg` → `CERT_CODE = AZ SA`, `CERT_NAME = Azure Solutions Architect`
- `assets/certs/gcp-pca.svg` → `CERT_CODE = GCP PCA`, `CERT_NAME = GCP Professional Cloud Architect`
- `assets/certs/databricks-de.svg` → `CERT_CODE = DB DE`, `CERT_NAME = Databricks Data Engineer`

- [ ] **Step 4: Create the architect-photo placeholder**

`assets/team/placeholder.svg`:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="Architect photo placeholder">
  <rect width="200" height="200" fill="#e5e7eb"/>
  <circle cx="100" cy="80" r="34" fill="#9ca3af"/>
  <path d="M40 180 Q100 120 160 180 Z" fill="#9ca3af"/>
</svg>
```

- [ ] **Step 5: Verify all asset files exist and open as images**

```bash
ls -la assets/partners/ assets/tracks/ assets/certs/ assets/team/placeholder.svg
```

Expected: 13 files listed. Open any one of them in a browser to confirm it renders as an image, not as raw XML.

- [ ] **Step 6: Commit**

```bash
git add assets/partners/ assets/tracks/ assets/certs/ assets/team/placeholder.svg
git commit -m "chore: add placeholder SVG assets for FDE page

Partner logos, Palantir training-track logo, cert badges, and architect-photo
placeholder. All neutral text-based SVGs. Official brand-kit assets to follow
in a separate change once usage approvals are in place."
```

---

## Task 4: Create `data/fde-practice.json` and schema doc

**Files:**
- Create: `data/fde-practice.json`
- Create: `data/fde-practice.schema.md`

- [ ] **Step 1: Write `data/fde-practice.json` with realistic seed content**

```json
{
  "feature_flags": {
    "partnerships_strip_visible": true,
    "roster_visible": true,
    "specializations_visible": true
  },

  "what_fde_does": [
    { "icon": "embed",    "title": "Embed",    "body": "Our FDEs work inside your team's tools, repos, and standups. They're not consultants on a Zoom — they're shipping with your engineers from day one." },
    { "icon": "build",    "title": "Build",    "body": "Production code, not slideware. FDEs leave behind running systems, tested, deployed, owned by your team." },
    { "icon": "transfer", "title": "Transfer", "body": "Every engagement ends with knowledge transfer. We document, pair, and review until your team can extend the work without us." },
    { "icon": "certify",  "title": "Certify",  "body": "Every FDE on our bench carries credentials from at least one major vendor ecosystem. You're hiring verifiable skill, not just a résumé." }
  ],

  "partnerships": [
    {
      "id": "anthropic",
      "name": "Anthropic",
      "logo": "assets/partners/anthropic.svg",
      "blurb_announceable": "Claude Partner Network member. Our architects hold Claude Certified Architect Foundations (CCAF) and ship production Claude integrations.",
      "blurb_pre_announce": "Our team is training through Anthropic Academy and is on the path to Claude Certified Architect Foundations (CCAF) certification.",
      "announceable": false
    },
    {
      "id": "microsoft",
      "name": "Microsoft",
      "logo": "assets/partners/microsoft.svg",
      "blurb_announceable": "Microsoft partner with Azure-certified architects across AI Services, Fabric, and Solutions Architecture.",
      "announceable": true
    },
    {
      "id": "aws",
      "name": "AWS",
      "logo": "assets/partners/aws.svg",
      "blurb_announceable": "AWS partner. Our bench includes Solutions Architect Professional and Machine Learning Specialty certified engineers.",
      "announceable": true
    },
    {
      "id": "google",
      "name": "Google Cloud",
      "logo": "assets/partners/google.svg",
      "blurb_announceable": "Google Cloud partner with Professional Cloud Architect and Professional Machine Learning Engineer certified staff.",
      "announceable": true
    },
    {
      "id": "databricks",
      "name": "Databricks",
      "logo": "assets/partners/databricks.svg",
      "blurb_announceable": "Databricks partner. Our engineers hold Data Engineer Professional and Machine Learning Professional certifications.",
      "announceable": true
    },
    {
      "id": "adobe",
      "name": "Adobe",
      "logo": "assets/partners/adobe.svg",
      "blurb_announceable": "Adobe partner working across Experience Platform, AEM, and Real-Time CDP implementations.",
      "announceable": true
    }
  ],

  "training_tracks": [
    {
      "id": "palantir-fde",
      "name": "Palantir Forward Deployed Engineer",
      "target_employer": "Palantir",
      "logo": "assets/tracks/palantir.svg",
      "blurb": "We train candidates against the Palantir FDE archetype: ontology design, Foundry and AIP fluency, and customer-embedded delivery practices.",
      "curriculum": [
        "Ontology design fundamentals",
        "Foundry and AIP hands-on labs",
        "Customer-embedded delivery practices",
        "Stakeholder communication and discovery"
      ],
      "candidates_training": 4,
      "candidates_ready": 0,
      "disclaimer": "Westley is not a Palantir partner. This track prepares candidates for the Palantir FDE role pattern."
    }
  ],

  "certifications": [
    { "id": "ccaf",          "name": "Claude Certified Architect Foundations", "issuer": "Anthropic", "badge": "assets/certs/ccaf.svg",          "blurb": "Anthropic's foundational architect certification covering Claude API design patterns, evaluation, safety, and enterprise integration." },
    { "id": "aws-sa-pro",    "name": "AWS Solutions Architect Pro",            "issuer": "AWS",       "badge": "assets/certs/aws-sa-pro.svg",    "blurb": "Senior-level AWS architecture certification covering multi-account, multi-region, and cost-optimized design." },
    { "id": "azure-sa",      "name": "Azure Solutions Architect Expert",       "issuer": "Microsoft", "badge": "assets/certs/azure-sa.svg",      "blurb": "Azure expert architect credential covering compute, networking, storage, and security at scale." },
    { "id": "gcp-pca",       "name": "GCP Professional Cloud Architect",       "issuer": "Google",    "badge": "assets/certs/gcp-pca.svg",       "blurb": "Google Cloud's professional architect certification covering design, planning, and operations on GCP." },
    { "id": "databricks-de", "name": "Databricks Data Engineer Professional",  "issuer": "Databricks","badge": "assets/certs/databricks-de.svg", "blurb": "Databricks' professional certification for production data engineering on the Lakehouse platform." }
  ],

  "architects": [
    { "name": "Architect 1", "role": "Senior FDE",       "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf", "aws-sa-pro"],          "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 2", "role": "Senior FDE",       "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf", "azure-sa"],            "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 3", "role": "Senior FDE",       "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf", "gcp-pca"],             "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 4", "role": "Senior FDE",       "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf", "databricks-de"],       "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 5", "role": "Mid-level FDE",    "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf"],                        "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 6", "role": "Mid-level FDE",    "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf"],                        "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 7", "role": "Mid-level FDE",    "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf"],                        "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 8", "role": "Mid-level FDE",    "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf"],                        "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 9", "role": "Junior FDE",       "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf"],                        "linkedin": "https://www.linkedin.com/in/", "in_training": true  },
    { "name": "Architect 10","role": "Junior FDE",       "photo": "assets/team/placeholder.svg", "cert_ids": ["ccaf"],                        "linkedin": "https://www.linkedin.com/in/", "in_training": true  }
  ],

  "engagement_models": [
    { "id": "staff-aug",   "title": "Staff augmentation",    "timeline": "1–6 months", "body": "An FDE joins your team full-time for the engagement, billed weekly. You direct the work; we handle the talent.", "fit": "Best when you have a clear roadmap but need senior capacity now." },
    { "id": "fixed-scope", "title": "Fixed-scope project",   "timeline": "4–12 weeks", "body": "We scope a defined deliverable — a Claude integration, a data pipeline, an MLOps stack — and ship it on a fixed bid.", "fit": "Best when the outcome is clear but the path is uncertain." },
    { "id": "direct-hire", "title": "Direct-hire placement", "timeline": "30–60 days", "body": "We source, vet, and present FDE candidates for your team. You employ them directly; we charge a placement fee.", "fit": "Best when you want long-term ownership and headcount." }
  ],

  "faq": [
    { "q": "How quickly can you put an FDE on-site?",            "a": "For staff augmentation, typically two to three weeks from signed engagement to first day. Fixed-scope projects begin once scope is locked, usually inside a week. Direct-hire placement runs 30–60 days end to end." },
    { "q": "How do you price engagements?",                      "a": "Staff augmentation: a weekly rate based on FDE seniority. Fixed-scope project: a fixed bid based on scope and risk. Direct-hire placement: a one-time fee based on first-year compensation. Specifics in the discovery call." },
    { "q": "What about NDAs and IP?",                            "a": "All engagements operate under mutual NDA. IP for fixed-scope and staff-augmentation work transfers to the client on payment. Direct-hire candidates own their own IP, of course." },
    { "q": "How are FDEs vetted?",                               "a": "Every FDE on our bench holds at least one major-vendor certification, has shipped production code, and has been interviewed by our delivery leads. We don't put generalists in front of clients." },
    { "q": "What if there's a mismatch in the first weeks?",     "a": "We replace the FDE inside 10 business days, at no additional cost. Mismatches are usually a signal we missed something in scoping; the replacement comes with a recalibrated brief." },
    { "q": "What's your geographic coverage?",                   "a": "Primarily US-based engineers, available for remote engagement worldwide and on-site work in North America. EMEA and APAC coverage growing through 2026." },
    { "q": "Can we trial an FDE before a full engagement?",      "a": "Yes. We offer a two-week trial against a defined task; if you don't want to continue, you owe the two weeks and nothing more." },
    { "q": "What happens at the end of an engagement?",          "a": "A documented handoff: code reviewed, systems documented, a transition session with your team, and 30 days of post-engagement availability for questions." }
  ]
}
```

- [ ] **Step 2: Validate the JSON parses**

```bash
node -e "JSON.parse(require('fs').readFileSync('data/fde-practice.json','utf-8')); console.log('OK')"
```

Expected output: `OK`. If you see a `SyntaxError`, fix the offending line and re-run.

- [ ] **Step 3: Write the schema doc `data/fde-practice.schema.md`**

```markdown
# `fde-practice.json` field reference

This file drives the dynamic content on `/forward-deployed`. Editing it is a
content task — no engineering required. Save the file, deploy, and the page
updates. If a field is missing or empty, the renderer skips it silently.

## Top-level keys

- `feature_flags` — section visibility toggles. Set any flag to `false` to
  hide that entire section, including its heading.
- `what_fde_does` — array of 4 mini-cards for the "What an FDE does" section.
- `partnerships` — array of vendor partnerships. Order matters; this is the
  display order in the partnerships strip.
- `training_tracks` — array of FDE specialization tracks (Palantir, etc.).
  **Not** partnerships; explicitly disclaimed in render.
- `certifications` — master list of certs. Architects reference these by id.
- `architects` — bench roster. Cert badges are resolved from `cert_ids`
  against `certifications`.
- `engagement_models` — three cards describing how to hire an FDE.
- `faq` — array of `{q, a}` pairs.

## `partnerships[]` entries

- `id` — stable id (e.g. `"anthropic"`).
- `name` — display name.
- `logo` — path to logo SVG.
- `blurb_announceable` — copy shown when the partnership is publicly announced.
- `blurb_pre_announce` — copy shown when `announceable: false`. Optional;
  if missing and `announceable` is false, the entire entry is skipped.
- `announceable` — boolean. `false` hides the partner badge and uses the
  pre-announcement blurb. `true` shows the badge and the announceable blurb.

**The Anthropic entry uses `announceable: false` until Anthropic clears
public announcement of the Claude Partner Network membership.** To flip:
change `false` to `true` and deploy. No code change.

## `training_tracks[]` entries

- `id`, `name`, `target_employer`, `logo`, `blurb` — straightforward strings.
- `curriculum` — array of curriculum-step strings.
- `candidates_training`, `candidates_ready` — integers.
- `disclaimer` — required string. Renders prominently to clarify this is
  not a partnership.

## `architects[]` entries

- `name`, `role`, `photo`, `linkedin` — strings.
- `cert_ids` — array of cert ids. Each id must match an entry in
  `certifications[].id` or the badge will be skipped.
- `in_training` — boolean. When `true`, cert badges render muted with an
  "in training" pill. Use this for architects who are mid-Academy.

## `certifications[]` entries

- `id`, `name`, `issuer`, `badge`, `blurb` — all strings.
- `id` is referenced by `architects[].cert_ids`.

## `engagement_models[]` entries

- `id`, `title`, `timeline`, `body`, `fit` — all strings.

## `faq[]` entries

- `q`, `a` — both strings.

## Editing safety

- The renderer skips records with missing required fields and logs a console
  warning instead of throwing.
- An empty array hides the section.
- A missing or unparseable JSON file leaves the static hero + section
  headings visible; dynamic sections silently absent.
```

- [ ] **Step 4: Update `firebase.json` to serve `data/*.json` with a short cache**

The existing config caches `js` and `css` for a year. We want the JSON file revalidated within minutes so content edits propagate fast. Add a new headers entry.

Current `firebase.json`:
```json
{
  "hosting": {
    "public": ".",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**",
      "README.md"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp|ico)",
        "headers": [
          { "key": "Cache-Control", "value": "max-age=31536000" }
        ]
      },
      {
        "source": "**/*.@(css|js)",
        "headers": [
          { "key": "Cache-Control", "value": "max-age=31536000" }
        ]
      }
    ],
    "cleanUrls": true,
    "trailingSlash": false
  }
}
```

Add a new headers entry for `data/*.json` *above* the css/js rule (Firebase Hosting applies the first matching rule). New full file:
```json
{
  "hosting": {
    "public": ".",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**",
      "README.md"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "data/**/*.json",
        "headers": [
          { "key": "Cache-Control", "value": "public, max-age=300" }
        ]
      },
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp|ico)",
        "headers": [
          { "key": "Cache-Control", "value": "max-age=31536000" }
        ]
      },
      {
        "source": "**/*.@(css|js)",
        "headers": [
          { "key": "Cache-Control", "value": "max-age=31536000" }
        ]
      }
    ],
    "cleanUrls": true,
    "trailingSlash": false
  }
}
```

This gives the JSON file a 5-minute browser cache while keeping every other asset on the long cache the site already uses.

- [ ] **Step 5: Commit**

```bash
git add data/fde-practice.json data/fde-practice.schema.md firebase.json
git commit -m "feat: add fde-practice.json data file, schema doc, and 5-min cache rule

Realistic seed content for partnerships (Anthropic gated to pre-announce),
Palantir training track with non-partnership disclaimer, 10 architects (all
in_training pre-CCAF completion), 5 certifications, 3 engagement models, 8
FAQ items. Schema doc in plain English for content editors. firebase.json
serves data/*.json with max-age=300 so content edits propagate within
5 minutes of deploy."
```

---

## Task 5: Build `js/fde-practice.js` skeleton with fetch + defensive failure

**Files:**
- Create: `js/fde-practice.js`

This task builds the entry point, the fetch loop, and the defensive-failure rules. Per-section renderers in Tasks 6–12 plug into the dispatch table at the bottom.

- [ ] **Step 1: Write the skeleton**

```javascript
// js/fde-practice.js
// Renders dynamic sections of /forward-deployed from data/fde-practice.json.
// Defensive: any missing field, empty array, or fetch failure is logged and
// silently skipped — static HTML always remains intact.

const DATA_URL = './data/fde-practice.json';

/**
 * Public entry point. Called from forward-deployed.html.
 * Fetches the data file and dispatches per-section renderers.
 */
export async function initFdePractice() {
  let data;
  try {
    const res = await fetch(DATA_URL, { cache: 'default' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
  } catch (err) {
    console.warn('[fde-practice] data fetch failed; dynamic sections will be absent:', err);
    return;
  }

  const flags = data.feature_flags || {};

  dispatch('what_fde_does',      data.what_fde_does,      'what-fde-does-mount',  renderWhatFdeDoes,      true);
  dispatch('partnerships',       data.partnerships,       'partnerships-mount',   renderPartnerships,     flags.partnerships_strip_visible !== false);
  dispatch('certifications',     data.certifications,     'certifications-mount', renderCertifications,   true);
  dispatch('architects',         data.architects,         'roster-mount',         (items, mount) => renderArchitects(items, data.certifications || [], mount), flags.roster_visible !== false);
  dispatch('training_tracks',    data.training_tracks,    'tracks-mount',         renderTrainingTracks,   flags.specializations_visible !== false);
  dispatch('engagement_models',  data.engagement_models,  'engagement-mount',     renderEngagementModels, true);
  dispatch('faq',                data.faq,                'faq-mount',            renderFaq,              true);
}

/**
 * Dispatch one section. If the data slice is missing/empty or the flag is
 * false, hide the section's wrapping <section> entirely (heading and all).
 */
function dispatch(name, items, mountId, renderer, sectionVisible) {
  const mount = document.getElementById(mountId);
  if (!mount) {
    console.warn(`[fde-practice] mount not found for ${name}: #${mountId}`);
    return;
  }
  const section = mount.closest('section');
  if (!sectionVisible || !Array.isArray(items) || items.length === 0) {
    if (section) section.hidden = true;
    return;
  }
  try {
    renderer(items, mount);
  } catch (err) {
    console.warn(`[fde-practice] renderer ${name} threw:`, err);
    if (section) section.hidden = true;
  }
}

// ---------- Per-section renderers (stubs, filled in Tasks 6–12) ----------

function renderWhatFdeDoes(items, mount) {
  // Filled in Task 6.
}

function renderPartnerships(items, mount) {
  // Filled in Task 7.
}

function renderCertifications(items, mount) {
  // Filled in Task 8.
}

function renderArchitects(items, certifications, mount) {
  // Filled in Task 9.
}

function renderTrainingTracks(items, mount) {
  // Filled in Task 10.
}

function renderEngagementModels(items, mount) {
  // Filled in Task 11.
}

function renderFaq(items, mount) {
  // Filled in Task 12.
}

// ---------- Shared helpers ----------

/**
 * Escape a string for safe insertion inside HTML text or attribute context.
 * Used by every renderer that emits user-editable content from the JSON.
 */
export function escapeHtml(value) {
  if (value == null) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/**
 * Required-field guard. Returns true if every named key on `record` is a
 * non-empty string. Logs a warning and returns false otherwise.
 */
export function hasFields(record, keys, contextLabel) {
  for (const k of keys) {
    if (typeof record[k] !== 'string' || record[k].length === 0) {
      console.warn(`[fde-practice] ${contextLabel} missing required field "${k}":`, record);
      return false;
    }
  }
  return true;
}
```

- [ ] **Step 2: Verify the page still loads, fetch succeeds, all dynamic sections hide**

Run `python3 -m http.server 8000` from repo root. Load `http://localhost:8000/forward-deployed.html` in a browser with DevTools open.

Expected:
- The Network tab shows a successful `200` for `data/fde-practice.json`.
- The Console shows no warnings.
- All dynamic sections (`#what-fde-does`, `#partnerships`, etc.) are hidden because every renderer is still a no-op stub — `dispatch` calls them, they return without populating, but the section itself is *not* hidden by `dispatch` because items are non-empty. **Wait — this is wrong.** Re-read the logic: `dispatch` only hides the section if the items array is empty or the flag is false. Since the JSON has populated arrays, the renderers run, but they're no-ops, so the mount stays empty *and the section stays visible with an empty mount underneath*. This is the expected intermediate state until Tasks 6–12 fill the renderers.

So the correct expectation is: every section heading and lead text is visible, but every mount `<div>` underneath is empty. No console warnings.

- [ ] **Step 3: Verify the fetch-failure path**

In DevTools, open the Network tab, find the row for `fde-practice.json`, right-click → "Block request URL" (Chrome) or equivalent. Reload the page.

Expected:
- A console warning: `[fde-practice] data fetch failed; dynamic sections will be absent: ...`.
- The hero, sub-nav, every section heading, the final CTA, and the footer remain visible.
- The page does not display a visible error to the visitor.

Un-block the URL when done.

- [ ] **Step 4: Commit**

```bash
git add js/fde-practice.js
git commit -m "feat: add fde-practice.js entry point with defensive fetch and dispatch

initFdePractice fetches data/fde-practice.json and dispatches per-section
renderers. Renderers are stubs at this commit; Tasks 6–12 fill them. The
dispatch helper hides sections on missing data, empty arrays, or feature
flags set to false. Fetch failures and renderer exceptions are logged but
never surface as visible errors."
```

---

## Task 6: Implement `renderWhatFdeDoes`

**Files:**
- Modify: `js/fde-practice.js` (`renderWhatFdeDoes` stub)
- Modify: `styles.css` (append FDE grid + card styles)

- [ ] **Step 1: Replace the `renderWhatFdeDoes` stub**

In `js/fde-practice.js`, replace:
```javascript
function renderWhatFdeDoes(items, mount) {
  // Filled in Task 6.
}
```

with:
```javascript
function renderWhatFdeDoes(items, mount) {
  const cards = items
    .filter(item => hasFields(item, ['title', 'body'], 'what_fde_does'))
    .map(item => `
      <article class="fde-card fde-what-card">
        <div class="fde-card-icon" aria-hidden="true" data-icon="${escapeHtml(item.icon || '')}"></div>
        <h3>${escapeHtml(item.title)}</h3>
        <p>${escapeHtml(item.body)}</p>
      </article>
    `)
    .join('');
  mount.innerHTML = cards;
}
```

- [ ] **Step 2: Append styles to `styles.css`**

Add at the bottom of `styles.css`:
```css
/* ===================================
   FDE Practice page
   =================================== */

.fde-section { padding-block: clamp(3rem, 6vw, 5rem); }

.fde-section .section-heading {
  font-family: var(--font-display);
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: var(--text-dark);
}

.fde-section .section-lead {
  color: var(--text-muted);
  max-width: 60ch;
  margin-bottom: 2rem;
}

.fde-grid {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.fde-card {
  background: var(--light-surface);
  border: 1px solid hsl(210, 15%, 90%);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px hsl(210, 15%, 90%, 0.4);
}

.fde-card h3 {
  font-size: 1.1rem;
  margin: 0.5rem 0 0.5rem;
  color: var(--text-dark);
}

.fde-card p {
  color: var(--text-muted);
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0;
}

.fde-card-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--gradient-primary);
}
```

- [ ] **Step 3: Verify in the browser**

Run `python3 -m http.server 8000`. Load `http://localhost:8000/forward-deployed.html`.

Expected:
- The "What an FDE does" section shows four cards (Embed, Build, Transfer, Certify) in a responsive grid.
- Each card has a small colored icon block at the top, a title, and a body paragraph.
- On mobile width (≤480 px), cards stack to one column.

- [ ] **Step 4: Verify defensive behavior**

Edit `data/fde-practice.json`. Find the first entry in `what_fde_does` and delete its `title` field. Save. Reload the page.

Expected:
- That entry's card does **not** appear (only three cards render).
- Console shows: `[fde-practice] what_fde_does missing required field "title": {...}`.

Restore the `title` field. Save.

- [ ] **Step 5: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: render the 'What an FDE does' section

Four mini-cards from data.what_fde_does. Cards skip silently if required
fields are missing. Adds the fde-card / fde-grid styles all subsequent
sections will share."
```

---

## Task 7: Implement `renderPartnerships` with `announceable` gating

**Files:**
- Modify: `js/fde-practice.js`
- Modify: `styles.css`

- [ ] **Step 1: Replace the `renderPartnerships` stub**

```javascript
function renderPartnerships(items, mount) {
  const cards = items
    .map(item => {
      // Always need name + logo
      if (!hasFields(item, ['name', 'logo'], 'partnerships')) return '';

      const announceable = item.announceable === true;
      const blurb = announceable ? item.blurb_announceable : item.blurb_pre_announce;

      // If no usable blurb for the current announce state, skip this partner.
      if (typeof blurb !== 'string' || blurb.length === 0) {
        if (!announceable) {
          console.warn(`[fde-practice] partnership "${item.id}" pre-announce blurb missing; skipping until announceable`);
        } else {
          console.warn(`[fde-practice] partnership "${item.id}" announceable blurb missing; skipping`);
        }
        return '';
      }

      const badge = announceable
        ? `<span class="fde-partner-badge" aria-label="Partner badge">Partner</span>`
        : `<span class="fde-partner-badge fde-partner-badge-pending" aria-label="Pre-announcement">In progress</span>`;

      return `
        <article class="fde-partner-card${announceable ? '' : ' fde-partner-card-pending'}">
          <img class="fde-partner-logo" src="${escapeHtml(item.logo)}" alt="${escapeHtml(item.name)} logo" loading="lazy">
          <div class="fde-partner-body">
            <header>
              <h3>${escapeHtml(item.name)}</h3>
              ${badge}
            </header>
            <p>${escapeHtml(blurb)}</p>
          </div>
        </article>
      `;
    })
    .join('');
  mount.innerHTML = cards;
}
```

- [ ] **Step 2: Append partnership styles to `styles.css`**

```css
.fde-partners-strip {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
}

.fde-partner-card {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 1.25rem;
  background: var(--light-surface);
  border: 1px solid hsl(210, 15%, 90%);
  border-radius: 12px;
}

.fde-partner-card-pending {
  border-style: dashed;
  background: hsl(210, 20%, 98%);
}

.fde-partner-logo {
  width: 80px;
  height: 32px;
  flex-shrink: 0;
  object-fit: contain;
}

.fde-partner-body h3 {
  margin: 0 0 0.25rem;
  font-size: 1.05rem;
  display: inline-block;
  margin-right: 0.5rem;
}

.fde-partner-body p {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.92rem;
  line-height: 1.5;
}

.fde-partner-badge {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background: var(--primary-color);
  color: white;
  vertical-align: middle;
}

.fde-partner-badge-pending {
  background: hsl(210, 8%, 80%);
  color: var(--text-dark);
}
```

- [ ] **Step 3: Verify the pre-announcement state**

Reload `http://localhost:8000/forward-deployed.html`.

Expected:
- Six partner cards in a responsive grid.
- Five (Microsoft, AWS, Google Cloud, Databricks, Adobe) render with a solid border, the announceable blurb, and a "Partner" badge.
- The Anthropic card renders with a dashed border, the pre-announce blurb ("Our team is training through Anthropic Academy and is on the path to..."), and an "In progress" badge — **no "Partner" / "Member" language**.

- [ ] **Step 4: Verify the announcement-flip behavior**

Edit `data/fde-practice.json`. Find the Anthropic entry and change `"announceable": false` to `"announceable": true`. Save and reload.

Expected:
- The Anthropic card now renders with a solid border, the **announceable** blurb ("Claude Partner Network member..."), and a "Partner" badge.

Revert to `"announceable": false` and save before proceeding.

- [ ] **Step 5: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: render partnerships strip with per-partner announceable gating

Each partner card flips between announceable and pre-announce blurbs based
on the per-record announceable flag. The Anthropic entry uses pre-announce
state until cleared; flipping it to true is a one-line JSON edit and
requires no code change."
```

---

## Task 8: Implement `renderCertifications`

**Files:**
- Modify: `js/fde-practice.js`
- Modify: `styles.css`

- [ ] **Step 1: Replace the `renderCertifications` stub**

```javascript
function renderCertifications(items, mount) {
  const cards = items
    .filter(item => hasFields(item, ['id', 'name', 'issuer', 'badge'], 'certifications'))
    .map(item => `
      <article class="fde-cert-card">
        <img class="fde-cert-badge" src="${escapeHtml(item.badge)}" alt="${escapeHtml(item.name)} badge" loading="lazy">
        <div>
          <h3>${escapeHtml(item.name)}</h3>
          <p class="fde-cert-issuer">Issued by ${escapeHtml(item.issuer)}</p>
          ${item.blurb ? `<p class="fde-cert-blurb">${escapeHtml(item.blurb)}</p>` : ''}
        </div>
      </article>
    `)
    .join('');
  mount.innerHTML = cards;
}
```

- [ ] **Step 2: Append cert styles to `styles.css`**

```css
.fde-cert-legend {
  display: grid;
  gap: 1.25rem;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}

.fde-cert-card {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
  padding: 1.25rem;
  background: var(--light-surface);
  border: 1px solid hsl(210, 15%, 90%);
  border-radius: 12px;
}

.fde-cert-badge {
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}

.fde-cert-card h3 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  color: var(--text-dark);
}

.fde-cert-issuer {
  margin: 0 0 0.5rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.fde-cert-blurb {
  margin: 0;
  font-size: 0.92rem;
  line-height: 1.5;
  color: var(--text-muted);
}
```

- [ ] **Step 3: Verify**

Reload the page. Expected: five cert cards (CCAF, AWS SAP, Azure SA, GCP PCA, Databricks DE) each with a badge image, a name, an issuer line, and a blurb.

- [ ] **Step 4: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: render the certifications legend

Five cert cards with badge, name, issuer, and blurb. Powers cert-badge
lookups used by the architect roster in Task 9."
```

---

## Task 9: Implement `renderArchitects` (cert badge resolution + in_training)

**Files:**
- Modify: `js/fde-practice.js`
- Modify: `styles.css`

- [ ] **Step 1: Replace the `renderArchitects` stub**

```javascript
function renderArchitects(items, certifications, mount) {
  // Build a lookup: id -> cert object
  const certById = new Map();
  for (const c of certifications) {
    if (c && typeof c.id === 'string') certById.set(c.id, c);
  }

  const cards = items
    .filter(item => hasFields(item, ['name', 'role', 'photo'], 'architects'))
    .map(item => {
      const inTraining = item.in_training === true;
      const certIds = Array.isArray(item.cert_ids) ? item.cert_ids : [];
      const badges = certIds
        .map(id => certById.get(id))
        .filter(c => c)
        .map(c => `
          <img class="fde-cert-mini${inTraining ? ' fde-cert-mini-muted' : ''}"
               src="${escapeHtml(c.badge)}"
               alt="${escapeHtml(c.name)} badge"
               title="${escapeHtml(c.name)}"
               loading="lazy">
        `)
        .join('');

      const linkedinLink = typeof item.linkedin === 'string' && item.linkedin.length > 0
        ? `<a class="fde-architect-linkedin" href="${escapeHtml(item.linkedin)}" rel="noopener noreferrer" target="_blank" aria-label="${escapeHtml(item.name)} on LinkedIn">LinkedIn</a>`
        : '';

      return `
        <article class="fde-architect-card">
          <img class="fde-architect-photo" src="${escapeHtml(item.photo)}" alt="${escapeHtml(item.name)}" loading="lazy">
          <div class="fde-architect-body">
            <h3>${escapeHtml(item.name)}</h3>
            <p class="fde-architect-role">${escapeHtml(item.role)}</p>
            ${inTraining ? `<span class="fde-pill fde-pill-training">In training</span>` : ''}
            <div class="fde-architect-badges">${badges}</div>
            ${linkedinLink}
          </div>
        </article>
      `;
    })
    .join('');

  mount.innerHTML = cards;
}
```

- [ ] **Step 2: Append architect styles to `styles.css`**

```css
.fde-roster {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.fde-architect-card {
  background: var(--light-surface);
  border: 1px solid hsl(210, 15%, 90%);
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
}

.fde-architect-photo {
  width: 96px;
  height: 96px;
  border-radius: 50%;
  object-fit: cover;
  margin: 0 auto 0.75rem;
  display: block;
}

.fde-architect-body h3 {
  margin: 0 0 0.25rem;
  font-size: 1rem;
  color: var(--text-dark);
}

.fde-architect-role {
  margin: 0 0 0.5rem;
  color: var(--text-muted);
  font-size: 0.88rem;
}

.fde-architect-badges {
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-block: 0.75rem;
}

.fde-cert-mini {
  width: 28px;
  height: 28px;
}

.fde-cert-mini-muted {
  opacity: 0.45;
  filter: grayscale(0.8);
}

.fde-pill {
  display: inline-block;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.fde-pill-training {
  background: hsl(40, 90%, 92%);
  color: hsl(30, 70%, 30%);
}

.fde-architect-linkedin {
  display: inline-block;
  margin-top: 0.5rem;
  font-size: 0.85rem;
  color: var(--primary-color);
  text-decoration: none;
}

.fde-architect-linkedin:hover {
  text-decoration: underline;
}
```

- [ ] **Step 3: Verify**

Reload. Expected:
- Ten architect cards in a grid (3 wide on desktop, 2 on tablet, 1 on mobile).
- Each card: placeholder photo (silhouette SVG), name, role.
- Each card shows an "In training" pill (because every architect has `in_training: true` in the seed JSON).
- Cert badges below the name are muted/grayscale (because of `in_training`).
- Architects 1–4 show 2 badges each; architects 5–10 show 1 badge each.

- [ ] **Step 4: Verify the in_training flip**

Edit `data/fde-practice.json`. Find Architect 1 and change `"in_training": true` to `"in_training": false`. Save and reload.

Expected:
- Architect 1's card no longer shows the "In training" pill.
- Architect 1's two cert badges render at full color (no grayscale, full opacity).

Revert to `true` and save.

- [ ] **Step 5: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: render architect roster with cert-badge resolution and in_training state

Each architect resolves cert_ids against the shared certifications lookup.
in_training=true mutes the cert badges and shows an 'In training' pill,
letting the roster ship before the 10 Academy enrollees complete CCAF."
```

---

## Task 10: Implement `renderTrainingTracks` (Palantir + disclaimer)

**Files:**
- Modify: `js/fde-practice.js`
- Modify: `styles.css`

- [ ] **Step 1: Replace the `renderTrainingTracks` stub**

```javascript
function renderTrainingTracks(items, mount) {
  const cards = items
    .filter(item => hasFields(item, ['name', 'target_employer', 'logo', 'blurb', 'disclaimer'], 'training_tracks'))
    .map(item => {
      const curriculum = Array.isArray(item.curriculum) && item.curriculum.length > 0
        ? `<ul class="fde-track-curriculum">${item.curriculum.map(line => `<li>${escapeHtml(line)}</li>`).join('')}</ul>`
        : '';

      const stats = [];
      if (Number.isInteger(item.candidates_training) && item.candidates_training > 0) {
        stats.push(`${item.candidates_training} currently training`);
      }
      if (Number.isInteger(item.candidates_ready) && item.candidates_ready > 0) {
        stats.push(`${item.candidates_ready} ready for placement`);
      }
      const statsLine = stats.length ? `<p class="fde-track-stats">${escapeHtml(stats.join(' · '))}</p>` : '';

      return `
        <article class="fde-track-card">
          <img class="fde-track-logo" src="${escapeHtml(item.logo)}" alt="${escapeHtml(item.name)} track">
          <h3>${escapeHtml(item.name)}</h3>
          <p class="fde-track-target">Target role: ${escapeHtml(item.target_employer)} Forward Deployed Engineer</p>
          <p class="fde-track-blurb">${escapeHtml(item.blurb)}</p>
          ${curriculum}
          ${statsLine}
          <p class="fde-track-disclaimer" role="note">${escapeHtml(item.disclaimer)}</p>
        </article>
      `;
    })
    .join('');
  mount.innerHTML = cards;
}
```

- [ ] **Step 2: Append track styles to `styles.css`**

```css
.fde-tracks {
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
}

.fde-track-card {
  background: hsl(210, 20%, 98%);
  border: 2px dashed hsl(210, 15%, 80%);
  border-radius: 12px;
  padding: 1.5rem;
}

.fde-track-logo {
  height: 48px;
  width: auto;
  margin-bottom: 0.75rem;
}

.fde-track-card h3 {
  margin: 0 0 0.25rem;
  color: var(--text-dark);
}

.fde-track-target {
  margin: 0 0 0.75rem;
  font-size: 0.88rem;
  color: var(--text-muted);
}

.fde-track-blurb {
  margin: 0 0 0.75rem;
  font-size: 0.95rem;
  color: var(--text-dark);
}

.fde-track-curriculum {
  margin: 0 0 0.75rem;
  padding-left: 1.25rem;
  color: var(--text-muted);
  font-size: 0.92rem;
}

.fde-track-curriculum li { margin-bottom: 0.25rem; }

.fde-track-stats {
  margin: 0 0 0.75rem;
  font-size: 0.88rem;
  color: var(--primary-dark);
  font-weight: 500;
}

.fde-track-disclaimer {
  margin: 0;
  padding: 0.75rem;
  background: hsl(40, 90%, 95%);
  border-left: 3px solid hsl(30, 70%, 50%);
  font-size: 0.85rem;
  color: var(--text-dark);
}
```

- [ ] **Step 3: Verify**

Reload. Expected:
- One training-track card under "FDE specializations we train for."
- Title: "Palantir Forward Deployed Engineer."
- "Target role: Palantir Forward Deployed Engineer."
- A 4-item curriculum list.
- A stats line: "4 currently training."
- A clearly highlighted disclaimer at the bottom: "Westley is not a Palantir partner. This track prepares candidates for the Palantir FDE role pattern."
- The card is visually distinct from the partner cards (dashed border, different background).

- [ ] **Step 4: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: render FDE training tracks with non-partnership disclaimer

Palantir Forward Deployed Engineer track renders with curriculum, training
counts, and a prominently-styled disclaimer making clear Westley is not a
Palantir partner. Visual treatment is intentionally distinct from the
partnership strip so the two categories cannot be confused."
```

---

## Task 11: Implement `renderEngagementModels`

**Files:**
- Modify: `js/fde-practice.js`
- Modify: `styles.css`

- [ ] **Step 1: Replace the `renderEngagementModels` stub**

```javascript
function renderEngagementModels(items, mount) {
  const cards = items
    .filter(item => hasFields(item, ['title', 'timeline', 'body', 'fit'], 'engagement_models'))
    .map(item => `
      <article class="fde-card fde-engagement-card">
        <h3>${escapeHtml(item.title)}</h3>
        <p class="fde-engagement-timeline">${escapeHtml(item.timeline)}</p>
        <p>${escapeHtml(item.body)}</p>
        <p class="fde-engagement-fit"><strong>Best fit:</strong> ${escapeHtml(item.fit)}</p>
      </article>
    `)
    .join('');
  mount.innerHTML = cards;
}
```

- [ ] **Step 2: Append engagement styles to `styles.css`**

```css
.fde-engagement-card {
  display: flex;
  flex-direction: column;
}

.fde-engagement-timeline {
  margin: 0 0 0.75rem;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--primary-dark);
}

.fde-engagement-fit {
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid hsl(210, 15%, 92%);
  font-size: 0.9rem;
  color: var(--text-muted);
}
```

- [ ] **Step 3: Verify**

Reload. Expected: three engagement cards (Staff augmentation / Fixed-scope project / Direct-hire placement). Each shows timeline pill, body, and "Best fit" line at the bottom.

- [ ] **Step 4: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: render the three engagement-model cards"
```

---

## Task 12: Implement `renderFaq`

**Files:**
- Modify: `js/fde-practice.js`
- Modify: `styles.css`

- [ ] **Step 1: Replace the `renderFaq` stub**

```javascript
function renderFaq(items, mount) {
  const entries = items
    .filter(item => hasFields(item, ['q', 'a'], 'faq'))
    .map(item => `
      <details class="fde-faq-item">
        <summary>${escapeHtml(item.q)}</summary>
        <p>${escapeHtml(item.a)}</p>
      </details>
    `)
    .join('');
  mount.innerHTML = entries;
}
```

- [ ] **Step 2: Append FAQ styles to `styles.css`**

```css
.fde-faq {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-width: 760px;
  margin-inline: auto;
}

.fde-faq-item {
  background: var(--light-surface);
  border: 1px solid hsl(210, 15%, 90%);
  border-radius: 8px;
  padding: 0;
}

.fde-faq-item summary {
  cursor: pointer;
  padding: 1rem 1.25rem;
  font-weight: 600;
  color: var(--text-dark);
  list-style: none;
}

.fde-faq-item summary::-webkit-details-marker { display: none; }

.fde-faq-item summary::after {
  content: '+';
  float: right;
  font-weight: 400;
  font-size: 1.25rem;
  color: var(--text-muted);
}

.fde-faq-item[open] summary::after { content: '–'; }

.fde-faq-item p {
  margin: 0;
  padding: 0 1.25rem 1.25rem;
  color: var(--text-muted);
  line-height: 1.6;
}

.fde-faq-item summary:focus-visible {
  outline: 2px solid var(--primary-color);
  outline-offset: -2px;
  border-radius: 8px;
}
```

- [ ] **Step 3: Verify**

Reload. Expected: 8 FAQ items in a stacked list. Clicking a question expands the answer; a `+` becomes `–`. Pressing Tab moves focus through the items, Enter expands each. Keyboard navigation works without mouse.

- [ ] **Step 4: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: render FAQ as native details/summary with keyboard support"
```

---

## Task 13: Sticky in-page sub-nav with mobile dropdown

**Files:**
- Modify: `styles.css`
- Modify: `forward-deployed.html` (already contains the sub-nav markup from Task 1)

The sub-nav HTML is already in place (Task 1). This task adds sticky positioning, an active-section indicator on scroll, and a mobile-dropdown treatment. The active-indicator behavior uses the `IntersectionObserver` API — kept inline because it's only used on this page.

- [ ] **Step 1: Append sub-nav styles to `styles.css`**

```css
.fde-subnav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: var(--light-surface);
  border-bottom: 1px solid hsl(210, 15%, 90%);
  box-shadow: 0 1px 3px hsl(210, 15%, 0%, 0.04);
}

.fde-subnav ul {
  list-style: none;
  display: flex;
  gap: 1.5rem;
  margin: 0;
  padding: 0.75rem 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.fde-subnav ul::-webkit-scrollbar { display: none; }

.fde-subnav a {
  text-decoration: none;
  color: var(--text-muted);
  font-size: 0.9rem;
  font-weight: 500;
  white-space: nowrap;
  padding: 0.25rem 0;
  border-bottom: 2px solid transparent;
  transition: color 0.15s ease, border-color 0.15s ease;
}

.fde-subnav a:hover { color: var(--text-dark); }

.fde-subnav a.fde-subnav-active {
  color: var(--primary-color);
  border-bottom-color: var(--primary-color);
}

/* Mobile: subnav scrolls horizontally on small screens; layout is unchanged. */
@media (max-width: 640px) {
  .fde-subnav ul { padding-block: 0.6rem; gap: 1.25rem; }
}
```

- [ ] **Step 2: Add the active-section observer to `js/fde-practice.js`**

Append this function to the file, and call it from `initFdePractice` after `dispatch` calls complete.

In `initFdePractice`, just before the closing brace, add:
```javascript
  initSubnavObserver();
```

Then append at the bottom of the file:
```javascript
/**
 * Highlight the sub-nav link for the section currently in view.
 * Pure additive: if the observer can't be created or no links match,
 * the sub-nav still works as plain anchor links.
 */
function initSubnavObserver() {
  if (!('IntersectionObserver' in window)) return;

  const links = Array.from(document.querySelectorAll('.fde-subnav a[href^="#"]'));
  if (links.length === 0) return;

  const linkByTarget = new Map();
  const sections = [];
  for (const link of links) {
    const id = link.getAttribute('href').slice(1);
    const target = document.getElementById(id);
    if (target) {
      linkByTarget.set(target, link);
      sections.push(target);
    }
  }
  if (sections.length === 0) return;

  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const link = linkByTarget.get(entry.target);
      if (!link) continue;
      if (entry.isIntersecting) {
        links.forEach(l => l.classList.remove('fde-subnav-active'));
        link.classList.add('fde-subnav-active');
      }
    }
  }, { rootMargin: '-40% 0px -55% 0px', threshold: 0 });

  sections.forEach(s => observer.observe(s));
}
```

- [ ] **Step 3: Verify desktop behavior**

Reload at desktop width. Expected:
- The sub-nav sticks to the top of the viewport once scrolled past the hero.
- Clicking a sub-nav link smoothly jumps to that section.
- As you scroll, the active sub-nav link's color flips to `--primary-color` and gains an underline.

- [ ] **Step 4: Verify mobile behavior**

Open DevTools, switch to mobile viewport (e.g., iPhone 12 — 390 × 844). Reload.

Expected:
- The sub-nav row scrolls horizontally with overflow.
- All six links remain accessible by horizontal scroll.
- Tapping a link still jumps to the section.
- The hamburger nav from the main navbar still works (handled by existing `script.js`).

- [ ] **Step 5: Commit**

```bash
git add js/fde-practice.js styles.css
git commit -m "feat: sticky sub-nav with active-section observer

Sub-nav row sticks below the main navbar. IntersectionObserver tracks which
section is currently visible and applies fde-subnav-active to the
corresponding link. Falls back to plain anchor behavior on browsers without
IntersectionObserver."
```

---

## Task 14: Final smoke checklist run

Run the full manual smoke from the spec (`docs/superpowers/specs/2026-05-18-fde-practice-page-design.md` §11) end to end before declaring the feature done.

- [ ] **Step 1: Full page scroll, desktop**

Run `python3 -m http.server 8000`. Load `http://localhost:8000/forward-deployed.html` at 1440 px width.

Verify in order: hero → sub-nav (sticky) → What an FDE does (4 cards) → Partnerships (6 cards, Anthropic pre-announce state) → Certifications (5) → Roster (10 architects, all in training) → Specializations (Palantir track with disclaimer) → Engagement (3 cards) → FAQ (8 items, collapse/expand) → Final CTA → Footer.

- [ ] **Step 2: Fetch-failure resilience**

DevTools → Network → block `fde-practice.json`. Reload.

Expected: static hero, sub-nav links, every section heading, lead text, final CTA, and footer remain. Dynamic mounts empty. Console warning fires. No visible error. Un-block.

- [ ] **Step 3: Anthropic announcement flip**

Edit `data/fde-practice.json`, set `partnerships[0].announceable` to `true`, save, reload.

Expected: Anthropic card shows the announceable blurb and a "Partner" badge with the primary-color background. **Revert to `false` before deploying.**

- [ ] **Step 4: Architect graduation flip**

Edit `data/fde-practice.json`, set `architects[0].in_training` to `false`, save, reload.

Expected: Architect 1's card loses the "In training" pill; cert badges render at full color. **Revert to `true` before deploying.**

- [ ] **Step 5: Mobile viewport**

DevTools → 390 × 844. Reload.

Expected: hero copy reflows, sub-nav scrolls horizontally, all card grids collapse to one column, FAQ items remain readable and tappable.

- [ ] **Step 6: Keyboard navigation**

Disconnect the mouse. Reload. Tab through the page.

Expected: focus moves through main nav → sub-nav links → CTAs → FAQ summaries → final-CTA link → footer. Every focused element has a visible focus ring. Enter on a sub-nav link jumps to that section. Enter on a FAQ summary expands the answer.

- [ ] **Step 7: Console hygiene**

After all the above, reload one more time with default settings. The console should be silent — no warnings, no errors.

- [ ] **Step 8: Commit any fixes**

If steps 1–7 surfaced bugs, fix them inline in the relevant task's file, re-verify, and commit:
```bash
git add <files>
git commit -m "fix: <one-line description of the issue and fix>"
```

If no fixes were needed, no commit for this task.

---

## Task 15 (optional, recommended): JSON Schema validation in CI

This task catches typos and missing required fields in `data/fde-practice.json` before they ship. Only worth doing if non-engineers will edit the file directly; skip if you're the only editor for the foreseeable future.

**Files:**
- Create: `data/fde-practice.schema.json`
- Create: `.github/workflows/validate-data.yml`

- [ ] **Step 1: Write the JSON Schema**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "FDE Practice content schema",
  "type": "object",
  "required": ["partnerships", "training_tracks", "architects", "certifications", "engagement_models", "faq", "what_fde_does"],
  "properties": {
    "feature_flags": {
      "type": "object",
      "properties": {
        "partnerships_strip_visible": { "type": "boolean" },
        "roster_visible": { "type": "boolean" },
        "specializations_visible": { "type": "boolean" }
      }
    },
    "what_fde_does": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["title", "body"],
        "properties": {
          "icon": { "type": "string" },
          "title": { "type": "string", "minLength": 1 },
          "body": { "type": "string", "minLength": 1 }
        }
      }
    },
    "partnerships": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "logo", "announceable"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "logo": { "type": "string" },
          "blurb_announceable": { "type": "string" },
          "blurb_pre_announce": { "type": "string" },
          "announceable": { "type": "boolean" }
        }
      }
    },
    "training_tracks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "target_employer", "logo", "blurb", "disclaimer"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "target_employer": { "type": "string" },
          "logo": { "type": "string" },
          "blurb": { "type": "string" },
          "curriculum": { "type": "array", "items": { "type": "string" } },
          "candidates_training": { "type": "integer", "minimum": 0 },
          "candidates_ready": { "type": "integer", "minimum": 0 },
          "disclaimer": { "type": "string" }
        }
      }
    },
    "certifications": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "name", "issuer", "badge"],
        "properties": {
          "id": { "type": "string" },
          "name": { "type": "string" },
          "issuer": { "type": "string" },
          "badge": { "type": "string" },
          "blurb": { "type": "string" }
        }
      }
    },
    "architects": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "role", "photo"],
        "properties": {
          "name": { "type": "string" },
          "role": { "type": "string" },
          "photo": { "type": "string" },
          "cert_ids": { "type": "array", "items": { "type": "string" } },
          "linkedin": { "type": "string" },
          "in_training": { "type": "boolean" }
        }
      }
    },
    "engagement_models": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "timeline", "body", "fit"],
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "timeline": { "type": "string" },
          "body": { "type": "string" },
          "fit": { "type": "string" }
        }
      }
    },
    "faq": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["q", "a"],
        "properties": {
          "q": { "type": "string" },
          "a": { "type": "string" }
        }
      }
    }
  }
}
```

- [ ] **Step 2: Write the GitHub Action workflow**

```yaml
# .github/workflows/validate-data.yml
name: Validate fde-practice data

on:
  push:
    paths:
      - 'data/fde-practice.json'
      - 'data/fde-practice.schema.json'
      - '.github/workflows/validate-data.yml'
  pull_request:
    paths:
      - 'data/fde-practice.json'
      - 'data/fde-practice.schema.json'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm install --no-save ajv ajv-cli
      - run: npx ajv validate -s data/fde-practice.schema.json -d data/fde-practice.json
```

- [ ] **Step 3: Verify the workflow catches a bad edit (locally before push)**

Install `ajv-cli` locally and run the same validation command:
```bash
npx --yes ajv-cli validate -s data/fde-practice.schema.json -d data/fde-practice.json
```

Expected: `data/fde-practice.json valid`.

Now break the file: delete the `name` field on the first partnership. Save. Re-run:
```bash
npx --yes ajv-cli validate -s data/fde-practice.schema.json -d data/fde-practice.json
```

Expected: exit code non-zero, error mentioning `must have required property 'name'`. Restore the field.

- [ ] **Step 4: Commit**

```bash
git add data/fde-practice.schema.json .github/workflows/validate-data.yml
git commit -m "ci: validate data/fde-practice.json against JSON Schema on push and PR

Catches typos and missing required fields before they ship. ajv-cli runs in
GitHub Actions on pushes that touch the data file or schema."
```

---

## Wrap-up

After Task 14 (and optionally Task 15), the feature is complete:

- `/forward-deployed` renders with full content.
- All six partner cards render correctly; Anthropic stays pre-announcement until you flip its flag and deploy.
- All ten architects render in their "in training" state until Anthropic Academy completion lets you flip them individually.
- The page is keyboard-accessible, mobile-responsive, and degrades gracefully if `fde-practice.json` fails to load.
- Editing the roster, FAQ, or partner blurbs requires only a JSON edit + deploy.

**Open the PR with this checklist in the body so the reviewer can scan it.** Reference the design spec (`docs/superpowers/specs/2026-05-18-fde-practice-page-design.md`) in the PR description.

**Post-merge follow-ons (out of scope here, file as separate issues):**
1. Replace placeholder partner logos with official brand-kit assets, per each partner's brand guidelines.
2. Photograph and write bios for the ten architects; replace placeholder names and silhouettes.
3. Build `/forward-deployed/apply` for candidate intake.
4. Build `/partnerships` hub page and per-partner deep pages once needed.
5. Track `?topic=fde` leads separately in `contact.html`.
6. Add Schema.org `ProfessionalService` JSON-LD to `forward-deployed.html` for richer search-result presentation (spec §8 marks this optional).
