const express = require('express');
const cors = require('cors');
require('dotenv').config();
const { connectMongo, connectPostgres } = require('./config/db');
const { initBot } = require('./services/telegramBot');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Initialize Databases
connectMongo();
connectPostgres();

// Initialize Services
initBot();

// Routes
const jobRoutes = require('./routes/jobRoutes');
const adminRoutes = require('./routes/adminRoutes');
const contactRoutes = require('./routes/contactRoutes');

app.use('/api/jobs', jobRoutes);
app.use('/api/admin', adminRoutes);
app.use('/api/contact', contactRoutes);

// Health Check
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'VMS Portal Backend Running' });
});

// Start Server
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
