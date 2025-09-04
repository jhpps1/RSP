const express = require('express');
const path = require('path');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3000;
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// 미들웨어
app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// API URL을 프론트엔드에 전달
app.get('/config', (req, res) => {
    res.json({ apiUrl: API_URL });
});

// 메인 페이지
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// 서버 시작
app.listen(PORT, '0.0.0.0', () => {
    console.log(`Web server running on port ${PORT}`);
    console.log(`API URL: ${API_URL}`);
});