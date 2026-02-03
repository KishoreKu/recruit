# AGENTS.md

This file contains guidelines and commands for agentic coding agents working on the Westley Resource website.

## Project Overview

Westley Resource is a static HTML/CSS/JavaScript website for an IT recruiting firm. The site uses modern web technologies with no build process required and is deployed to Firebase Hosting.

## Build, Test, and Deployment Commands

### Development
```bash
# No build process required - static files
# Serve locally (optional)
python -m http.server 8000
# or
npx serve .
```

### Deployment
```bash
# Manual deployment to Firebase
firebase deploy --only hosting

# Install Firebase CLI (if needed)
npm install -g firebase-tools

# Login to Firebase (if needed)
firebase login
```

### Testing
```bash
# No automated test framework configured
# Manual testing required:
# 1. Open index.html in browser
# 2. Test all pages: index.html, about.html, services.html, employers.html, candidates.html, contact.html
# 3. Test responsive design on mobile/tablet/desktop
# 4. Test form submissions and navigation
# 5. Test contact form validation
```

### Linting/Validation
```bash
# HTML validation (optional)
npx html-validate *.html

# CSS validation (optional)
npx stylelint styles.css

# JavaScript validation (optional)
npx eslint script.js
```

## Project Structure

```
westleyresource/
├── index.html          # Homepage
├── about.html          # About page
├── services.html       # Services page
├── employers.html      # For Employers page
├── candidates.html     # For Candidates page
├── contact.html        # Contact page
├── styles.css          # Main stylesheet with design system
├── script.js           # Interactive functionality
├── firebase.json       # Firebase hosting configuration
├── .firebaserc         # Firebase project settings
├── .github/workflows/deploy.yml  # Auto-deployment workflow
└── assets/images/      # Image assets
```

## Code Style Guidelines

### HTML
- Use HTML5 semantic elements (`<nav>`, `<section>`, `<main>`, `<article>`, etc.)
- Include proper meta tags for SEO and accessibility
- Use semantic class naming (BEM-like pattern)
- Validate HTML with W3C validator
- Include `alt` attributes for all images
- Use ARIA labels where appropriate for accessibility

### CSS
- Follow CSS custom properties (variables) system defined in `:root`
- Use mobile-first responsive design
- Organize styles with clear section comments
- Use logical order: Base → Layout → Components → Utilities
- Maintain consistent spacing using the defined scale (--spacing-xs to --spacing-2xl)
- Use HSL colors for better consistency and maintainability
- Apply consistent border radius using --radius-* variables
- Use CSS Grid and Flexbox for layouts
- Maintain consistent typography with defined font families

### JavaScript
- Use ES6+ features with proper browser compatibility checks
- Wrap code in `DOMContentLoaded` event listener
- Use descriptive variable names with camelCase
- Add comprehensive comments for major functionality blocks
- Use modern DOM queries (`querySelector`, `querySelectorAll`)
- Implement proper error handling and validation
- Use semantic event delegation where appropriate
- Follow the existing modular structure with clear section separators
- Use template literals for string interpolation
- Implement proper form validation before submission

### Naming Conventions
- Files: kebab-case (e.g., `contact-form.html`)
- CSS classes: BEM-like pattern with hyphens (e.g., `nav-toggle`, `card__title`)
- JavaScript variables: camelCase (e.g., `navToggle`, `formValidation`)
- IDs: kebab-case for HTML anchors (e.g., `contact-section`)

## Design System

### Colors
- Primary: `--primary-color` (hsl(210, 60%, 45%))
- Secondary: `--secondary-color` (hsl(200, 20%, 50%))
- Accent: `--accent-color` (hsl(25, 70%, 55%))
- Success: `--success-color` (hsl(150, 40%, 45%))
- Neutrals: Defined as `--dark-bg`, `--light-bg`, `--text-dark`, etc.

### Typography
- Primary font: Inter
- Display font: Roboto
- Tagline font: Open Sans

### Spacing
- Use defined spacing scale: --spacing-xs (0.5rem) to --spacing-2xl (6rem)
- Maintain consistent margins and padding throughout

## Common Patterns

### Navigation
- Mobile hamburger menu with toggle functionality
- Active state highlighting for current page
- Smooth scroll for anchor links
- Scroll-based navbar styling changes

### Forms
- Client-side validation for all required fields
- Email format validation using regex
- Success/error notification system
- Form reset after successful submission

### Responsive Design
- Mobile-first approach
- Breakpoints defined for tablet and desktop
- Flexible grid layouts using CSS Grid
- Responsive typography scaling

## Deployment Workflow

The site automatically deploys to Firebase Hosting on every push to the `main` branch via GitHub Actions.

### Manual Deployment Steps
1. Run `firebase deploy --only hosting`
2. Deployment targets: westleyresource-5131d.firebaseapp.com
3. Custom domain: westleyresource.com (configured in Firebase console)

## Browser Support
- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

## Important Notes

- No build process or bundling required
- All assets should be optimized for web (compressed images, minified CSS/JS if desired)
- Maintain semantic HTML structure for SEO
- Test all interactive elements on mobile devices
- Ensure forms work without backend (client-side validation only)
- Keep contact information consistent across all pages
- Use relative paths for internal links
- Test cross-browser compatibility before deploying

## Error Handling

- Implement try-catch blocks for JavaScript operations
- Provide user-friendly error messages
- Use the notification system for feedback
- Validate all user inputs before processing
- Gracefully handle missing DOM elements