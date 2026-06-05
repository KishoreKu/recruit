const { onRequest } = require('firebase-functions/v2/https');
const { defineSecret } = require('firebase-functions/params');
const axios = require('axios');

const MS_TENANT_ID = defineSecret('MS_TENANT_ID');
const MS_CLIENT_ID = defineSecret('MS_CLIENT_ID');
const MS_CLIENT_SECRET = defineSecret('MS_CLIENT_SECRET');
const MS_SENDER = defineSecret('MS_SENDER');

const getAccessToken = async (tenantId, clientId, clientSecret) => {
  const { data } = await axios.post(
    `https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token`,
    new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: clientId,
      client_secret: clientSecret,
      scope: 'https://graph.microsoft.com/.default',
    }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );
  return data.access_token;
};

exports.contact = onRequest(
  { secrets: [MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET, MS_SENDER], cors: true },
  async (req, res) => {
    if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

    const { type, name, company, email, phone, subject, message, hearAbout } = req.body;
    if (!name || !email || !subject || !message || !type) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    try {
      const token = await getAccessToken(
        MS_TENANT_ID.value(),
        MS_CLIENT_ID.value(),
        MS_CLIENT_SECRET.value()
      );

      await axios.post(
        `https://graph.microsoft.com/v1.0/users/${MS_SENDER.value()}/sendMail`,
        {
          message: {
            subject: `[Contact Form] ${subject}`,
            body: {
              contentType: 'HTML',
              content: `
                <h2>New Contact Form Submission</h2>
                <table cellpadding="8" style="border-collapse:collapse;">
                  <tr><td><b>Type</b></td><td>${type}</td></tr>
                  <tr><td><b>Name</b></td><td>${name}</td></tr>
                  <tr><td><b>Company</b></td><td>${company || '—'}</td></tr>
                  <tr><td><b>Email</b></td><td><a href="mailto:${email}">${email}</a></td></tr>
                  <tr><td><b>Phone</b></td><td>${phone || '—'}</td></tr>
                  <tr><td><b>Subject</b></td><td>${subject}</td></tr>
                  <tr><td><b>How heard</b></td><td>${hearAbout || '—'}</td></tr>
                </table>
                <h3>Message</h3>
                <p style="white-space:pre-wrap;">${message}</p>
              `,
            },
            toRecipients: [{ emailAddress: { address: MS_SENDER.value() } }],
            replyTo: [{ emailAddress: { address: email, name } }],
          },
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      res.json({ success: true });
    } catch (err) {
      console.error('Contact email error:', err.response?.data || err.message);
      res.status(500).json({ error: 'Failed to send message' });
    }
  }
);
