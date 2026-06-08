# Graph Report - .  (2026-06-06)

## Corpus Check
- 77 files · ~97,729 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 301 nodes · 289 edges · 55 communities (25 shown, 30 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 8 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Rawmessage Express Group|Rawmessage Express Group]]
- [[_COMMUNITY_Package Json Group|Package Json Group]]
- [[_COMMUNITY_Sendcontactemail Submitcontact Group|Sendcontactemail Submitcontact Group]]
- [[_COMMUNITY_React Dom Group|React Dom Group]]
- [[_COMMUNITY_Package Json Group|Package Json Group]]
- [[_COMMUNITY_Career Coach Group|Career Coach Group]]
- [[_COMMUNITY_Firebase Functions Group|Firebase Functions Group]]
- [[_COMMUNITY_Fde Practice Group|Fde Practice Group]]
- [[_COMMUNITY_Visible Fde Group|Visible Fde Group]]
- [[_COMMUNITY_Package Json Group|Package Json Group]]
- [[_COMMUNITY_Gstack Github Group|Gstack Github Group]]
- [[_COMMUNITY_Apply Jobs Group|Apply Jobs Group]]
- [[_COMMUNITY_Test Crash Group|Test Crash Group]]
- [[_COMMUNITY_Practice Fde Group|Practice Fde Group]]
- [[_COMMUNITY_Westleyresource Westley Group|Westleyresource Westley Group]]
- [[_COMMUNITY_Job Admin Group|Job Admin Group]]
- [[_COMMUNITY_Form Contact Group|Form Contact Group]]
- [[_COMMUNITY_Check Gstack Group|Check Gstack Group]]
- [[_COMMUNITY_Settings Local Group|Settings Local Group]]
- [[_COMMUNITY_Brain Circuit Group|Brain Circuit Group]]
- [[_COMMUNITY_Westley Resource Group|Westley Resource Group]]
- [[_COMMUNITY_Westley Resource Group|Westley Resource Group]]
- [[_COMMUNITY_Script Shownotification Group|Script Shownotification Group]]
- [[_COMMUNITY_Deployment Workflow Group|Deployment Workflow Group]]
- [[_COMMUNITY_Aws Solutions Group|Aws Solutions Group]]
- [[_COMMUNITY_Azure Solutions Group|Azure Solutions Group]]
- [[_COMMUNITY_Ccaf Badge Group|Ccaf Badge Group]]
- [[_COMMUNITY_Databricks Data Group|Databricks Data Group]]
- [[_COMMUNITY_Check Dns Group|Check Dns Group]]
- [[_COMMUNITY_Adobe Logo Group|Adobe Logo Group]]
- [[_COMMUNITY_Databricks Logo Group|Databricks Logo Group]]
- [[_COMMUNITY_Microsoft Logo Group|Microsoft Logo Group]]
- [[_COMMUNITY_Palantir Fde Group|Palantir Fde Group]]
- [[_COMMUNITY_Gstack Plugin Group|Gstack Plugin Group]]
- [[_COMMUNITY_Test Crash Group|Test Crash Group]]
- [[_COMMUNITY_Gcp Professional Group|Gcp Professional Group]]
- [[_COMMUNITY_Vite Api Group|Vite Api Group]]
- [[_COMMUNITY_Anthropic Logo Group|Anthropic Logo Group]]
- [[_COMMUNITY_Aws Logo Group|Aws Logo Group]]
- [[_COMMUNITY_Google Cloud Group|Google Cloud Group]]
- [[_COMMUNITY_Jobs Group|Jobs Group]]
- [[_COMMUNITY_Raw Messages Group|Raw Messages Group]]
- [[_COMMUNITY_Saved Jobs Group|Saved Jobs Group]]
- [[_COMMUNITY_Users Group|Users Group]]
- [[_COMMUNITY_Claude Partner Group|Claude Partner Group]]
- [[_COMMUNITY_Fde Practice Group|Fde Practice Group]]
- [[_COMMUNITY_Team Placeholder Group|Team Placeholder Group]]
- [[_COMMUNITY_Design System Group|Design System Group]]
- [[_COMMUNITY_Gstack Group|Gstack Group]]
- [[_COMMUNITY_Dynatrace Deployment Group|Dynatrace Deployment Group]]
- [[_COMMUNITY_Firebase Hosting Group|Firebase Hosting Group]]

## God Nodes (most connected - your core abstractions)
1. `hosting` - 7 edges
2. `processRawJob()` - 5 edges
3. `sendContactEmail()` - 5 edges
4. `authMiddleware()` - 4 edges
5. `scripts` - 4 edges
6. `feature_flags` - 4 edges
7. `escapeHtml()` - 4 edges
8. `hasFields()` - 4 edges
9. `main()` - 4 edges
10. `app` - 4 edges

## Surprising Connections (you probably didn't know these)
- `contact` --semantically_similar_to--> `sendContactEmail()`  [INFERRED] [semantically similar]
  functions/index.js → server/services/mailer.js
- `getAccessToken()` --semantically_similar_to--> `getAccessToken()`  [INFERRED] [semantically similar]
  functions/index.js → server/services/mailer.js
- `Deployment Workflow` --semantically_similar_to--> `Firebase Hosting`  [INFERRED] [semantically similar]
  AGENTS.md → README.md
- `Architecture & Infrastructure` --semantically_similar_to--> `Firebase Hosting`  [INFERRED] [semantically similar]
  GEMINI.md → README.md
- `Contact Form Implementation` --conceptually_related_to--> `Form Validation Logic`  [INFERRED]
  GEMINI.md → script.js

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Contact Form Infrastructure** — westleyresource_gemini_contact_form, westleyresource_gemini_microsoft_graph_api, westleyresource_gemini_firebase_secret_manager, westleyresource_script_form_validation [INFERRED 0.85]
- **VMS Job Aggregator React Frontend** — src_app_router, pages_admindashboard_component, pages_jobdetail_component, pages_joblist_component [INFERRED 0.95]
- **Career Coach Backend Services** — carrercoach_server_stripe_integration, carrercoach_server_auth_routes, carrercoach_server_payment_routes, carrercoach_server_ai_routes, carrercoach_server_authmiddleware [INFERRED 0.95]
- **FDE Practice Page Content System** — data_fde_practice_content, data_fde_practice_schema_doc, plans_2026_05_18_fde_practice_page_plan, plans_2026_05_18_fde_practice_page_fde_practice [INFERRED 0.85]
- **Database Connections** — config_db_connectmongo, config_db_connectpostgres, config_db_pool [EXTRACTED 1.00]
- **API Controllers** — controllers_admincontroller_getrawmessages, controllers_admincontroller_approverawmessage, controllers_admincontroller_finalizejob, controllers_contactcontroller_submitcontact, controllers_jobcontroller_getjobs, controllers_jobcontroller_getjobbyid, controllers_jobcontroller_processrawjob [INFERRED 0.85]

## Communities (55 total, 30 thin omitted)

### Community 0 - "Rawmessage Express Group"
Cohesion: 0.06
Nodes (38): connectMongo(), connectPostgres(), mongoose, { Pool }, approveRawMessage(), finalizeJob(), getRawMessages(), { pool } (+30 more)

### Community 1 - "Package Json Group"
Cohesion: 0.08
Nodes (23): author, dependencies, axios, body-parser, cors, dotenv, express, mongoose (+15 more)

### Community 2 - "Sendcontactemail Submitcontact Group"
Cohesion: 0.12
Nodes (17): { sendContactEmail }, submitContact(), axios, contact, { defineSecret }, getAccessToken(), MS_CLIENT_ID, MS_CLIENT_SECRET (+9 more)

### Community 3 - "React Dom Group"
Cohesion: 0.11
Nodes (17): dependencies, axios, lucide-react, react, react-dom, react-router-dom, devDependencies, vite (+9 more)

### Community 4 - "Package Json Group"
Cohesion: 0.12
Nodes (16): dependencies, bcryptjs, cors, dotenv, express, jsonwebtoken, stripe, description (+8 more)

### Community 5 - "Career Coach Group"
Cohesion: 0.12
Nodes (15): Career Coach AI Routes, app, Career Coach Auth Routes, authMiddleware(), bcrypt, cors, express, jwt (+7 more)

### Community 6 - "Firebase Functions Group"
Cohesion: 0.13
Nodes (14): functions, source, hosting, cleanUrls, headers, ignore, public, rewrites (+6 more)

### Community 7 - "Fde Practice Group"
Cohesion: 0.26
Nodes (8): dispatch(), escapeHtml(), hasFields(), initFdePractice(), initSubnavObserver(), renderEngagementModels(), renderFaq(), renderTrainingTracks()

### Community 8 - "Visible Fde Group"
Cohesion: 0.17
Nodes (11): architects, certifications, engagement_models, faq, feature_flags, partnerships_strip_visible, roster_visible, specializations_visible (+3 more)

### Community 9 - "Package Json Group"
Cohesion: 0.17
Nodes (11): author, description, engines, node, keywords, license, main, name (+3 more)

### Community 10 - "Gstack Github Group"
Cohesion: 0.18
Nodes (10): enabledPlugins, gstack@gstack-github, extraKnownMarketplaces, gstack-github, plugins, source, hooks, PreToolUse (+2 more)

### Community 12 - "Apply Jobs Group"
Cohesion: 0.70
Nodes (4): apply_to_visible_jobs(), login(), main(), search_jobs()

### Community 13 - "Test Crash Group"
Cohesion: 0.50
Nodes (3): app, express, stripe

### Community 14 - "Practice Fde Group"
Cohesion: 0.50
Nodes (4): FDE Practice Content Data, FDE Practice Schema Doc, Forward Deployed Engineers Practice, FDE Practice Page Implementation Plan

### Community 15 - "Westleyresource Westley Group"
Cohesion: 0.50
Nodes (4): westleyresource, Westley Resource Full Logo, CONNECTING TECH TALENT WITH TOMORROW, Circuit Brain Motif

### Community 16 - "Job Admin Group"
Cohesion: 0.50
Nodes (4): Admin Dashboard, Job Detail, Job List, VMS Job Aggregator Router

### Community 17 - "Form Contact Group"
Cohesion: 0.50
Nodes (4): Contact Form Implementation, Firebase Secret Manager, Microsoft Graph API, Form Validation Logic

### Community 20 - "Brain Circuit Group"
Cohesion: 0.67
Nodes (3): Brain AI Circuit Icon, Artificial Intelligence, Cybernetics

### Community 21 - "Westley Resource Group"
Cohesion: 1.00
Nodes (3): Westley Resource Logo, Connecting Tech Talent With Tomorrow, Westley Resource

### Community 22 - "Westley Resource Group"
Cohesion: 0.67
Nodes (3): Westley Resource Logo Symbol, Hexagon Gradient Background, Stylized Letter W

### Community 24 - "Deployment Workflow Group"
Cohesion: 0.67
Nodes (3): Deployment Workflow, Architecture & Infrastructure, Firebase Hosting

## Knowledge Gaps
- **190 isolated node(s):** `check-gstack.sh script`, `source`, `repo`, `plugins`, `gstack@gstack-github` (+185 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **30 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `check-gstack.sh script`, `source`, `repo` to the rest of the system?**
  _190 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Rawmessage Express Group` be split into smaller, more focused modules?**
  _Cohesion score 0.06475485661424607 - nodes in this community are weakly interconnected._
- **Should `Package Json Group` be split into smaller, more focused modules?**
  _Cohesion score 0.08333333333333333 - nodes in this community are weakly interconnected._
- **Should `Sendcontactemail Submitcontact Group` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._
- **Should `React Dom Group` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._
- **Should `Package Json Group` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._
- **Should `Career Coach Group` be split into smaller, more focused modules?**
  _Cohesion score 0.11764705882352941 - nodes in this community are weakly interconnected._