const mongoose = require('mongoose');

const RawMessageSchema = new mongoose.Schema({
  platform: { type: String, required: true }, // e.g., 'Telegram', 'WhatsApp'
  group_name: { type: String },
  message_text: { type: String, required: true },
  is_processed: { type: Boolean, default: false },
  created_at: { type: Date, default: Date.now },
  metadata: { type: Map, of: String } // For platform-specific data like message_id, chat_id
});

module.exports = mongoose.model('RawMessage', RawMessageSchema);
