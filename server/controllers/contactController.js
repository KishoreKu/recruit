const { sendContactEmail } = require('../services/mailer');

const submitContact = async (req, res) => {
  const { type, name, company, email, phone, subject, message, hearAbout } = req.body;

  if (!name || !email || !subject || !message || !type) {
    return res.status(400).json({ error: 'Missing required fields' });
  }

  try {
    await sendContactEmail({ type, name, company, email, phone, subject, message, hearAbout });
    res.json({ success: true });
  } catch (err) {
    console.error('Contact email error:', err);
    res.status(500).json({ error: 'Failed to send message' });
  }
};

module.exports = { submitContact };
