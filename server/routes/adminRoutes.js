const express = require('express');
const router = express.Router();
const { getRawMessages, approveRawMessage, finalizeJob } = require('../controllers/adminController');

// Admin Routes
router.get('/raw-messages', getRawMessages);
router.post('/approve-raw/:id', approveRawMessage);
router.post('/finalize-job/:id', finalizeJob);

module.exports = router;
