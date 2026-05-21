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

  dispatch('what_fde_does',     data.what_fde_does,     'what-fde-does-mount',  renderWhatFdeDoes,     true);
  dispatch('partnerships',      data.partnerships,      'partnerships-mount',   renderPartnerships,    flags.partnerships_strip_visible !== false);
  dispatch('certifications',    data.certifications,    'certifications-mount', renderCertifications,  true);
  dispatch('architects',        data.architects,        'roster-mount',         (items, mount) => renderArchitects(items, data.certifications || [], mount), flags.roster_visible !== false);
  dispatch('training_tracks',   data.training_tracks,   'tracks-mount',         renderTrainingTracks,  flags.specializations_visible !== false);
  dispatch('engagement_models', data.engagement_models, 'engagement-mount',     renderEngagementModels,true);
  dispatch('faq',               data.faq,               'faq-mount',            renderFaq,             true);

  initSubnavObserver();
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

// ---------- Per-section renderers ----------

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

function renderPartnerships(items, mount) {
  const cards = items
    .map(item => {
      if (!hasFields(item, ['name', 'logo'], 'partnerships')) return '';

      const announceable = item.announceable === true;
      const blurb = announceable ? item.blurb_announceable : item.blurb_pre_announce;

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

function renderArchitects(items, certifications, mount) {
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

// ---------- Sub-nav active-section observer ----------

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

// ---------- Shared helpers ----------

/**
 * Escape a string for safe insertion inside HTML text or attribute context.
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
