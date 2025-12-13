const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();

const app = express();
const port = 3000;

app.use(cors());
app.use(bodyParser.json());
app.use(express.static('public'));

// Connect to SQLite database
const db = new sqlite3.Database('./db.sqlite3', (err) => {
    if (err) {
        console.error('Error opening database', err.message);
    } else {
        console.log('Connected to the SQLite database.');
    }
});

app.get('/api/stations', (req, res) => {
    const sql = 'SELECT SiteName, Latitude, Longitude FROM Site';
    db.all(sql, [], (err, rows) => {
        if (err) {
            res.status(400).json({ "error": err.message });
            return;
        }
        res.json({
            "message": "success",
            "data": rows
        });
    });
});

app.post('/api/predict', (req, res) => {
    const { longitude, latitude, magnitude, depth } = req.body;

    if (!longitude || !latitude || !magnitude || !depth) {
        return res.status(400).json({ error: 'Missing parameters' });
    }

    const pythonProcess = spawn('python', ['predict.py', longitude, latitude, magnitude, depth]);

    let dataString = '';
    let errorString = '';

    pythonProcess.stdout.on('data', (data) => {
        dataString += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        errorString += data.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python process exited with code ${code}`);
            console.error(`Error: ${errorString}`);
            return res.status(500).json({ error: 'Prediction failed', details: errorString });
        }

        try {
            const result = JSON.parse(dataString);
            res.json(result);
        } catch (e) {
            console.error('Failed to parse Python output:', dataString);
            res.status(500).json({ error: 'Invalid output from model', output: dataString });
        }
    });
});

app.listen(port, () => {
    console.log(`Server running at http://localhost:${port}`);
});
