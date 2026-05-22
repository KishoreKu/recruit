# Westley Resource - IT Recruiting Website

A professional, modern website for Westley Resource, a premier IT recruiting firm specializing in connecting top technology talent with leading companies.

## 🌟 Features

- **Modern Design**: Premium aesthetic with gradients, glassmorphism, and smooth animations
- **Fully Responsive**: Mobile-first design that works on all devices
- **SEO Optimized**: Semantic HTML and proper meta tags for search visibility
- **Interactive Forms**: Contact forms with client-side validation
- **No Dependencies**: Pure HTML, CSS, and JavaScript - no frameworks required

## 📁 Project Structure

```
westleyresource/
├── index.html          # Homepage
├── about.html          # About page
├── services.html       # Services page
├── employers.html      # For Employers page
├── candidates.html     # For Candidates page
├── contact.html        # Contact page
├── styles.css          # Design system & styles
├── script.js           # Interactive functionality
└── README.md           # This file
```

## 🚀 Quick Start

1. Clone this repository
2. Open `index.html` in your browser
3. No build process required!

## 📄 Pages

- **Home**: Hero section, value propositions, and specializations
- **About**: Company story, mission, values, and team
- **Services**: Detailed IT recruiting specializations and process
- **For Employers**: Benefits, pricing, and hiring process
- **For Candidates**: Job opportunities and career resources
- **Contact**: Contact form, office information, and FAQ

## 🎨 Design System

The website uses CSS custom properties for consistent theming:

- Professional color palette (blues, purples, pinks)
- Modern typography (Inter, Outfit)
- Responsive spacing scale
- Smooth animations and transitions

## 🌐 Deployment

### Firebase Hosting (Google Cloud Platform)

This website is automatically deployed to Firebase Hosting on Google Cloud Platform via GitHub Actions.

#### Initial Setup

1. **Install Firebase CLI**:
   ```bash
   npm install -g firebase-tools
   ```

2. **Login to Firebase**:
   ```bash
   firebase login
   ```

3. **Create a Firebase project** at [Firebase Console](https://console.firebase.google.com/)
   - Project name: `westleyresource`
   - Enable Google Analytics (optional)

4. **Initialize Firebase in your project**:
   ```bash
   firebase init hosting
   ```
   - Select your Firebase project
   - Set public directory to `.` (current directory)
   - Configure as single-page app: No
   - Don't overwrite existing files

5. **Generate service account for GitHub Actions**:
   - Go to Firebase Console → Project Settings → Service Accounts
   - Click "Generate New Private Key"
   - Save the JSON file securely
   - Add it as a GitHub secret named `FIREBASE_SERVICE_ACCOUNT`

#### Manual Deployment

To deploy manually:
```bash
firebase deploy --only hosting
```

#### Automatic Deployment

Every push to the `main` branch automatically deploys to Firebase Hosting via GitHub Actions.

#### Custom Domain Configuration

1. Go to Firebase Console → Hosting
2. Click "Add custom domain"
3. Enter `westleyresource.com`
4. Follow DNS configuration instructions
5. Firebase will automatically provision SSL certificates


## 📧 Contact Information

- **Email**: info@westleyresource.com
- **Phone**: (555) 123-4567
- **Address**: 123 Tech Boulevard, San Francisco, CA 94105

## 📝 License

© 2026 Westley Resource. All rights reserved.

## 🤖 gstack Skills

This project uses [gstack](https://github.com/garrytan/gstack) for web browsing and automation tasks. When working on this project, use the `/browse` skill from gstack for all web browsing needs instead of other browser automation tools.

### Available gstack Skills:
- `/browse` - For web browsing and information gathering
- `/qa` - Quality assurance testing
- `/design-*` - Various design consultation and implementation skills
- `/plan-*` - Planning and review skills
- `/ship` / `/land-and-deploy` - Deployment and release skills
- And many more - see CLAUDE.md for the complete list

## 🛠️ Technical Details

- **HTML5**: Semantic markup
- **CSS3**: Custom properties, Flexbox, Grid
- **JavaScript**: ES6+ vanilla JavaScript
- **Fonts**: Google Fonts (Inter, Outfit)
- **Icons**: SVG icons embedded inline

## 🔧 Customization

To customize the website:

1. **Colors**: Edit CSS custom properties in `styles.css` (lines 15-30)
2. **Content**: Update HTML files directly
3. **Contact Info**: Update footer in all HTML files
4. **Forms**: Connect to your backend/email service in `script.js`

## 📱 Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers (iOS Safari, Chrome Mobile)

---

Built with ❤️ for Westley Resource
