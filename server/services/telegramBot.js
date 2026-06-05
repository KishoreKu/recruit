const { Telegraf } = require('telegraf');
const RawMessage = require('../models/RawMessage');
require('dotenv').config();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;

/**
 * Initializes the Telegram Bot to listen for job-related messages in groups.
 */
const initBot = () => {
  if (!BOT_TOKEN) {
    console.warn('TELEGRAM_BOT_TOKEN is missing. Telegram bot will not start.');
    return;
  }

  const bot = new Telegraf(BOT_TOKEN);

  // Middleware to log all incoming messages for debugging (optional)
  bot.use(async (ctx, next) => {
    // console.log('Message Received:', ctx.update);
    return next();
  });

  // Listen for text messages
  bot.on('text', async (ctx) => {
    const { chat, message } = ctx;

    // Filter messages: typically we only want to process group messages or specific DMs
    // Check if the message is from a group or supergroup
    if (chat.type === 'group' || chat.type === 'supergroup' || chat.type === 'channel') {
      try {
        const rawMessage = new RawMessage({
          platform: 'Telegram',
          group_name: chat.title || 'Private Group',
          message_text: message.text,
          metadata: {
            message_id: message.message_id.toString(),
            chat_id: chat.id.toString(),
            from_user: message.from ? message.from.username || message.from.first_name : 'Unknown'
          }
        });

        await rawMessage.save();
        // console.log(`[Telegram] Saved raw message from ${chat.title}`);
      } catch (err) {
        console.error('[Telegram Error] Failed to save raw message:', err);
      }
    }
  });

  bot.catch((err, ctx) => {
    console.error(`[Telegram Error] Bot encountered an error: ${err}`);
  });

  bot.launch()
    .then(() => console.log('Telegram Bot is running...'))
    .catch((err) => console.error('Failed to launch Telegram Bot:', err));

  // Enable graceful stop
  process.once('SIGINT', () => bot.stop('SIGINT'));
  process.once('SIGTERM', () => bot.stop('SIGTERM'));

  return bot;
};

module.exports = { initBot };
