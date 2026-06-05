const OpenAI = require('openai');
require('dotenv').config();

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

/**
 * Sends raw message text to OpenAI to extract structured job data.
 * @param {string} rawText The job posting text from social media.
 * @returns {Promise<Object>} Structured job object.
 */
const parseJobMessage = async (rawText) => {
  if (!process.env.OPENAI_API_KEY) {
    console.error('OPENAI_API_KEY is missing.');
    return null;
  }

  const prompt = `
    Extract structured job information from the following raw message text. 
    Return the result as a strictly valid JSON object. 
    If a field is not found, use null.
    
    Fields:
    - job_title (string)
    - company (string)
    - skills (array of strings)
    - location (string)
    - job_type (string: 'Full-time', 'Part-time', 'Contract', 'Remote', etc.)
    - salary (string)
    - contact (string: email, phone, or link)
    
    Message Text:
    "${rawText}"
    
    JSON Output:
  `;

  try {
    const response = await openai.chat.completions.create({
      model: "gpt-4-turbo-preview", // or "gpt-3.5-turbo"
      messages: [{ role: "user", content: prompt }],
      response_format: { type: "json_object" },
      temperature: 0.1,
    });

    const parsedData = JSON.parse(response.choices[0].message.content);
    return parsedData;
  } catch (err) {
    console.error('[AI Parser Error] Failed to parse message:', err);
    return null;
  }
};

module.exports = { parseJobMessage };
