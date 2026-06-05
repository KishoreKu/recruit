const axios = require('axios');

const getAccessToken = async () => {
  const { data } = await axios.post(
    `https://login.microsoftonline.com/${process.env.MS_TENANT_ID}/oauth2/v2.0/token`,
    new URLSearchParams({
      grant_type: 'client_credentials',
      client_id: process.env.MS_CLIENT_ID,
      client_secret: process.env.MS_CLIENT_SECRET,
      scope: 'https://graph.microsoft.com/.default',
    }),
    { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
  );
  return data.access_token;
};

const sendContactEmail = async ({ type, name, company, email, phone, subject, message, hearAbout }) => {
  const token = await getAccessToken();

  await axios.post(
    `https://graph.microsoft.com/v1.0/users/${process.env.MS_SENDER}/sendMail`,
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
        toRecipients: [{ emailAddress: { address: process.env.MS_SENDER } }],
        replyTo: [{ emailAddress: { address: email, name } }],
      },
    },
    { headers: { Authorization: `Bearer ${token}` } }
  );
};

module.exports = { sendContactEmail };
