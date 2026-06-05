const express = require('express');
const router = express.Router();
const { getJobs, getJobById } = require('../controllers/jobController');

// Public/Recruiter Job Routes
router.get('/', getJobs);
router.get('/:id', getJobById);

module.exports = router;
