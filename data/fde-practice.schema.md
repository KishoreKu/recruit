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
