/**
 * AI Career Coach — Node.js + Express + Stripe Backend
 * 
 * SETUP:
 *   npm install express stripe cors dotenv jsonwebtoken bcryptjs
 *   node server.js
 */

require('dotenv').config();
const express = require('express');
const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');

const app = express();

// ─── Middleware ───────────────────────────────────────────────────────────────
// Allow all origins for local development to prevent "failed to fetch" errors
app.use(cors({ origin: '*' }));

// Raw body needed for Stripe webhooks BEFORE json parser
app.use('/api/payments/webhook', express.raw({ type: 'application/json' }));
app.use(express.json());

// ─── In-memory DB (replace with PostgreSQL in production) ────────────────────
const users = {}; // { email: { id, name, email, passwordHash, plan, stripeCustomerId, subscriptionId, subscriptionStatus } }
const sessions = {}; // { userId: [{ type, createdAt, data }] }

// ─── Stripe Price IDs (create these in your Stripe dashboard) ────────────────
const PLANS = {
  Starter:   { priceId: process.env.STRIPE_STARTER_PRICE_ID,   amount: 4900,  name: 'Starter'   },
  Pro:       { priceId: process.env.STRIPE_PRO_PRICE_ID,       amount: 9900,  name: 'Pro'       },
  Executive: { priceId: process.env.STRIPE_EXECUTIVE_PRICE_ID, amount: 19900, name: 'Executive' },
};

// ─── Auth helpers ─────────────────────────────────────────────────────────────
function generateToken(user) {
  return jwt.sign(
    { id: user.id, email: user.email, plan: user.plan },
    process.env.JWT_SECRET || 'dev-secret-change-in-prod',
    { expiresIn: '30d' }
  );
}

function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'No token provided' });
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET || 'dev-secret-change-in-prod');
    next();
  } catch {
    res.status(401).json({ error: 'Invalid or expired token' });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// AUTH ROUTES
// ─────────────────────────────────────────────────────────────────────────────

// POST /api/auth/register
app.post('/api/auth/register', async (req, res) => {
  const { name, email, password } = req.body;
  if (!name || !email || !password)
    return res.status(400).json({ error: 'Name, email and password are required' });

  if (users[email])
    return res.status(409).json({ error: 'An account with this email already exists' });

  const passwordHash = await bcrypt.hash(password, 10);
  const id = 'usr_' + Date.now();

  // Create Stripe customer
  let stripeCustomerId = null;
  try {
    const customer = await stripe.customers.create({ name, email });
    stripeCustomerId = customer.id;
  } catch (e) {
    console.error('Stripe customer creation failed:', e.message);
  }

  users[email] = {
    id, name, email, passwordHash,
    plan: 'free',
    stripeCustomerId,
    subscriptionId: null,
    subscriptionStatus: null,
    createdAt: new Date().toISOString(),
  };
  sessions[id] = [];

  const token = generateToken(users[email]);
  res.json({ token, user: { id, name, email, plan: 'free' } });
});

// POST /api/auth/login
app.post('/api/auth/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password)
    return res.status(400).json({ error: 'Email and password are required' });

  const user = users[email];
  if (!user) return res.status(401).json({ error: 'Invalid email or password' });

  const valid = await bcrypt.compare(password, user.passwordHash);
  if (!valid) return res.status(401).json({ error: 'Invalid email or password' });

  const token = generateToken(user);
  res.json({
    token,
    user: { id: user.id, name: user.name, email: user.email, plan: user.plan }
  });
});

// GET /api/auth/me
app.get('/api/auth/me', authMiddleware, (req, res) => {
  const user = users[req.user.email];
  if (!user) return res.status(404).json({ error: 'User not found' });
  res.json({
    id: user.id, name: user.name, email: user.email,
    plan: user.plan, subscriptionStatus: user.subscriptionStatus
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// PAYMENT ROUTES
// ─────────────────────────────────────────────────────────────────────────────

// POST /api/payments/create-checkout
// Creates a Stripe Checkout session and returns the URL
app.post('/api/payments/create-checkout', authMiddleware, async (req, res) => {
  const { plan } = req.body;
  const planData = PLANS[plan];
  if (!planData) return res.status(400).json({ error: 'Invalid plan selected' });

  const user = users[req.user.email];
  if (!user) return res.status(404).json({ error: 'User not found' });

  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      customer: user.stripeCustomerId,
      line_items: [{ price: planData.priceId, quantity: 1 }],
      subscription_data: {
        trial_period_days: 7, // 7-day free trial
        metadata: { userId: user.id, plan: planData.name },
      },
      metadata: { userId: user.id, plan: planData.name },
      success_url: `${process.env.FRONTEND_URL}/dashboard?session_id={CHECKOUT_SESSION_ID}&plan=${plan}`,
      cancel_url:  `${process.env.FRONTEND_URL}/pricing?cancelled=true`,
    });

    res.json({ checkoutUrl: session.url, sessionId: session.id });
  } catch (e) {
    console.error('Stripe checkout error:', e.message);
    res.status(500).json({ error: 'Failed to create checkout session' });
  }
});

// POST /api/payments/create-portal
// Opens Stripe Customer Portal (manage subscription, cancel, update card)
app.post('/api/payments/create-portal', authMiddleware, async (req, res) => {
  const user = users[req.user.email];
  if (!user?.stripeCustomerId)
    return res.status(400).json({ error: 'No billing account found' });

  try {
    const portalSession = await stripe.billingPortal.sessions.create({
      customer: user.stripeCustomerId,
      return_url: `${process.env.FRONTEND_URL}/dashboard`,
    });
    res.json({ portalUrl: portalSession.url });
  } catch (e) {
    console.error('Stripe portal error:', e.message);
    res.status(500).json({ error: 'Failed to open billing portal' });
  }
});

// GET /api/payments/subscription
// Returns the current user's subscription status
app.get('/api/payments/subscription', authMiddleware, async (req, res) => {
  const user = users[req.user.email];
  if (!user) return res.status(404).json({ error: 'User not found' });

  if (!user.subscriptionId) {
    return res.json({ plan: 'free', status: null });
  }

  try {
    const subscription = await stripe.subscriptions.retrieve(user.subscriptionId);
    res.json({
      plan: user.plan,
      status: subscription.status,           // active | trialing | past_due | canceled
      trialEnd: subscription.trial_end,
      currentPeriodEnd: subscription.current_period_end,
      cancelAtPeriodEnd: subscription.cancel_at_period_end,
    });
  } catch (e) {
    res.status(500).json({ error: 'Failed to fetch subscription' });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// STRIPE WEBHOOK  (receives events from Stripe — most important route)
// ─────────────────────────────────────────────────────────────────────────────
app.post('/api/payments/webhook', (req, res) => {
  const sig = req.headers['stripe-signature'];
  let event;

  try {
    event = stripe.webhooks.constructEvent(
      req.body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET
    );
  } catch (e) {
    console.error('Webhook signature failed:', e.message);
    return res.status(400).send(`Webhook Error: ${e.message}`);
  }

  console.log('Stripe event received:', event.type);

  switch (event.type) {

    // ── Trial started / subscription activated ──────────────────────────────
    case 'checkout.session.completed': {
      const session = event.data.object;
      const userId = session.metadata?.userId;
      const plan   = session.metadata?.plan;
      const user   = Object.values(users).find(u => u.id === userId);
      if (user && plan) {
        user.plan = plan;
        user.subscriptionId = session.subscription;
        user.subscriptionStatus = 'trialing';
        console.log(`✓ User ${user.email} started ${plan} trial`);
      }
      break;
    }

    // ── Subscription activated after trial ──────────────────────────────────
    case 'invoice.payment_succeeded': {
      const invoice = event.data.object;
      const subId   = invoice.subscription;
      const user    = Object.values(users).find(u => u.subscriptionId === subId);
      if (user) {
        user.subscriptionStatus = 'active';
        console.log(`✓ Payment succeeded for ${user.email}`);
      }
      break;
    }

    // ── Payment failed ───────────────────────────────────────────────────────
    case 'invoice.payment_failed': {
      const invoice = event.data.object;
      const subId   = invoice.subscription;
      const user    = Object.values(users).find(u => u.subscriptionId === subId);
      if (user) {
        user.subscriptionStatus = 'past_due';
        console.log(`✗ Payment failed for ${user.email} — plan downgraded`);
        // TODO: send payment failure email
      }
      break;
    }

    // ── Subscription cancelled ───────────────────────────────────────────────
    case 'customer.subscription.deleted': {
      const sub  = event.data.object;
      const user = Object.values(users).find(u => u.subscriptionId === sub.id);
      if (user) {
        user.plan = 'free';
        user.subscriptionId = null;
        user.subscriptionStatus = 'canceled';
        console.log(`✗ Subscription cancelled for ${user.email}`);
      }
      break;
    }

    // ── Plan upgraded/downgraded ─────────────────────────────────────────────
    case 'customer.subscription.updated': {
      const sub  = event.data.object;
      const user = Object.values(users).find(u => u.subscriptionId === sub.id);
      if (user) {
        user.subscriptionStatus = sub.status;
        // Update plan from metadata if changed
        if (sub.metadata?.plan) user.plan = sub.metadata.plan;
        console.log(`✓ Subscription updated for ${user.email}: ${sub.status}`);
      }
      break;
    }
  }

  res.json({ received: true });
});

// ─────────────────────────────────────────────────────────────────────────────
// SESSION / USAGE ROUTES
// ─────────────────────────────────────────────────────────────────────────────

// Plan usage limits
const PLAN_LIMITS = {
  free:      { analyses: 1,         roadmaps: 1,         interviews: 3        },
  Starter:   { analyses: 3,         roadmaps: 3,         interviews: 10       },
  Pro:       { analyses: Infinity,  roadmaps: Infinity,  interviews: Infinity },
  Executive: { analyses: Infinity,  roadmaps: Infinity,  interviews: Infinity },
};

// POST /api/sessions/log  — log a usage event
app.post('/api/sessions/log', authMiddleware, (req, res) => {
  const { type, data } = req.body; // type: 'analysis' | 'roadmap' | 'interview'
  const user = users[req.user.email];
  if (!user) return res.status(404).json({ error: 'User not found' });

  if (!sessions[user.id]) sessions[user.id] = [];

  // Check monthly usage
  const thisMonth = new Date();
  thisMonth.setDate(1); thisMonth.setHours(0,0,0,0);
  const monthSessions = sessions[user.id].filter(s =>
    new Date(s.createdAt) >= thisMonth && s.type === type
  );

  const limits = PLAN_LIMITS[user.plan] || PLAN_LIMITS.free;
  const limit  = limits[type + 's'] ?? limits.analyses;

  if (monthSessions.length >= limit) {
    return res.status(403).json({
      error: `You have reached your monthly ${type} limit on the ${user.plan} plan.`,
      upgradeRequired: true,
    });
  }

  sessions[user.id].push({ type, data, createdAt: new Date().toISOString() });
  res.json({ logged: true, usedThisMonth: monthSessions.length + 1, limit });
});

// GET /api/sessions/usage  — get current month usage
app.get('/api/sessions/usage', authMiddleware, (req, res) => {
  const user = users[req.user.email];
  if (!user) return res.status(404).json({ error: 'User not found' });

  const thisMonth = new Date();
  thisMonth.setDate(1); thisMonth.setHours(0,0,0,0);
  const userSessions = (sessions[user.id] || []).filter(s =>
    new Date(s.createdAt) >= thisMonth
  );

  const limits = PLAN_LIMITS[user.plan] || PLAN_LIMITS.free;
  const count  = (type) => userSessions.filter(s => s.type === type).length;

  res.json({
    plan: user.plan,
    usage: {
      analyses:   { used: count('analysis'),  limit: limits.analyses   },
      roadmaps:   { used: count('roadmap'),   limit: limits.roadmaps   },
      interviews: { used: count('interview'), limit: limits.interviews  },
    }
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// AI GENERATION ROUTE
// ─────────────────────────────────────────────────────────────────────────────
app.post('/api/ai/generate', authMiddleware, async (req, res) => {
  const { system, userPrompt } = req.body;
  if (!system || !userPrompt) {
    return res.status(400).json({ error: 'System and userPrompt are required' });
  }

  try {
    const openRouterRes = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`
      },
      body: JSON.stringify({
        model: 'google/gemini-2.0-flash-exp:free',
        messages: [
          { role: 'system', content: system },
          { role: 'user', content: userPrompt }
        ]
      })
    });

    if (!openRouterRes.ok) {
      const err = await openRouterRes.text();
      console.error('OpenRouter Error:', err);
      return res.status(openRouterRes.status).json({ error: 'AI generation failed' });
    }

    const data = await openRouterRes.json();
    const text = data.choices?.[0]?.message?.content || '';
    res.json({ text });
  } catch (e) {
    console.error('AI Route Error:', e.message);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// ─────────────────────────────────────────────────────────────────────────────
// HEALTH CHECK
// ─────────────────────────────────────────────────────────────────────────────
app.get('/health', (_, res) => res.json({ status: 'ok', timestamp: new Date().toISOString() }));

// ─────────────────────────────────────────────────────────────────────────────
const PORT = process.env.PORT || 4000;
app.listen(PORT, () => {
  console.log(`\n🚀 Career Coach API running on http://localhost:${PORT}`);
  console.log(`   Stripe mode: ${process.env.STRIPE_SECRET_KEY?.startsWith('sk_live') ? '🟢 LIVE' : '🟡 TEST'}\n`);
});
