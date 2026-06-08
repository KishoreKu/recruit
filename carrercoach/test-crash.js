const express = require('express');
const stripe = require('stripe')('sk_test_fake');
const app = express();
app.use(express.json());

app.post('/test', async (req, res) => {
  try {
    const session = await stripe.checkout.sessions.create({
      mode: 'subscription',
      customer: null,
      line_items: [{ price: undefined, quantity: 1 }],
      subscription_data: {
        trial_period_days: 7,
        metadata: { userId: '123', plan: 'Pro' },
      },
      metadata: { userId: '123', plan: 'Pro' },
      success_url: `http://localhost/dashboard`,
      cancel_url:  `http://localhost/pricing`,
    });
    res.json({ checkoutUrl: session.url });
  } catch (e) {
    console.log("CAUGHT:", e.message);
    res.status(500).json({ error: e.message });
  }
});
app.listen(4001, () => console.log("Listening"));
