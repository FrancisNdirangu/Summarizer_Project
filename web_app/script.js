// Load history and theme
let history = JSON.parse(localStorage.getItem('summaryHistory')) || [];
const body = document.body;
const theme = localStorage.getItem('theme') || 'light';
if (theme === 'dark') {
    body.classList.add('dark-theme');
    document.querySelector('.theme-toggle').textContent = '☀️ Light Mode';
}

// Toggle input sections
document.querySelectorAll('input[name="input-mode"]').forEach(radio => {
    radio.addEventListener('change', () => {
        document.getElementById('text-input').style.display = radio.value === 'text' ? 'block' : 'none';
        document.getElementById('url-input').style.display = radio.value === 'url' ? 'block' : 'none';
        document.getElementById('pdf-input').style.display = radio.value === 'pdf' ? 'block' : 'none';
        document.getElementById('summary-output').style.display = 'none';
    });
});

// Toggle theme
function toggleTheme() {
    body.classList.toggle('dark-theme');
    const isDark = body.classList.contains('dark-theme');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
    document.querySelector('.theme-toggle').textContent = isDark ? '☀️ Light Mode' : '🌙 Dark Mode';
}

// Toggle sidebar
function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
}

// Update history
function updateHistory() {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = '';
    history.forEach((entry, index) => {
        const div = document.createElement('div');
        div.className = 'history-entry';
        div.innerHTML = `
            <h4>Summary ${index + 1} (${entry.timestamp})</h4>
            <p><strong>Input:</strong> ${entry.input.substring(0, 50)}...</p>
            <p><strong>Summary:</strong> ${entry.summary.substring(0, 50)}...</p>
        `;
        div.onclick = () => {
            document.getElementById('summary-output').style.display = 'block';
            document.getElementById('summary-text').textContent = entry.summary;
            document.getElementById('text-input').style.display = 'none';
            document.getElementById('url-input').style.display = 'none';
            document.getElementById('pdf-input').style.display = 'none';
            if (entry.mode === 'text') {
                document.getElementById('blog-text').value = entry.input;
                document.querySelector('input[value="text"]').checked = true;
                document.getElementById('text-input').style.display = 'block';
            } else if (entry.mode === 'url') {
                document.getElementById('blog-url').value = entry.url || '';
                document.getElementById('extracted-content').textContent = entry.input;
                document.getElementById('extracted-text').style.display = 'block';
                document.querySelector('input[value="url"]').checked = true;
                document.getElementById('url-input').style.display = 'block';
            } else if (entry.mode === 'pdf') {
                document.getElementById('pdf-extracted-content').textContent = entry.input;
                document.getElementById('pdf-extracted-text').style.display = 'block';
                document.querySelector('input[value="pdf"]').checked = true;
                document.getElementById('pdf-input').style.display = 'block';
            }
        };
        historyList.appendChild(div);
    });
    localStorage.setItem('summaryHistory', JSON.stringify(history));
}

// Clear history
function clearHistory() {
    history = [];
    updateHistory();
}

// Extract text from URL
async function extractUrl() {
    const url = document.getElementById('blog-url').value;
    const statusDiv = document.getElementById('url-status');
    const extractedDiv = document.getElementById('extracted-text');
    const extractedContent = document.getElementById('extracted-content');
    const summarizeBtn = document.querySelector('.summarize-btn');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');

    if (!url) {
        statusDiv.innerHTML = '<span style="color: #dc3545;">Please enter a valid URL.</span>';
        return;
    }

    statusDiv.innerHTML = 'Extracting content...';
    btnText.style.display = 'none';
    spinner.style.display = 'inline-block';
    try {
        const response = await fetch('http://127.0.0.1:8000/extract_url/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        });
        const data = await response.json();
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
        if (response.ok) {
            statusDiv.innerHTML = '<span style="color: #22c55e;">Content extracted successfully!</span>';
            extractedContent.textContent = data.text;
            extractedDiv.style.display = 'block';
        } else {
            statusDiv.innerHTML = `<span style="color: #dc3545;">Failed to extract content: ${data.error}</span>`;
        }
    } catch (error) {
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
        statusDiv.innerHTML = `<span style="color: #dc3545;">Error: ${error.message}</span>`;
    }
}

// Upload and extract text from PDF
async function uploadPdf() {
    const fileInput = document.getElementById('pdf-file');
    const statusDiv = document.getElementById('pdf-status');
    const extractedDiv = document.getElementById('pdf-extracted-text');
    const extractedContent = document.getElementById('pdf-extracted-content');
    const summarizeBtn = document.querySelector('.summarize-btn');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');

    if (!fileInput.files[0]) {
        statusDiv.innerHTML = '<span style="color: #dc3545;">Please select a PDF file.</span>';
        return;
    }

    const file = fileInput.files[0];
    if (!file.name.endsWith('.pdf')) {
        statusDiv.innerHTML = '<span style="color: #dc3545;">Please upload a valid PDF file.</span>';
        return;
    }

    const formData = new FormData();
    formData.append('file', file);
    statusDiv.innerHTML = 'Uploading and extracting...';
    btnText.style.display = 'none';
    spinner.style.display = 'inline-block';
    try {
        const response = await fetch('http://127.0.0.1:8000/summarize_pdf/', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
        if (response.ok) {
            statusDiv.innerHTML = '<span style="color: #22c55e;">PDF content extracted successfully!</span>';
            extractedContent.textContent = data.text;
            extractedDiv.style.display = 'block';
        } else {
            statusDiv.innerHTML = `<span style="color: #dc3545;">Failed to extract PDF: ${data.error}</span>`;
        }
    } catch (error) {
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
        statusDiv.innerHTML = `<span style="color: #dc3545;">Error: ${error.message}</span>`;
    }
}

// Summarize content
async function summarize() {
    let text = '';
    let mode = document.querySelector('input[name="input-mode"]:checked').value;
    const summaryOutput = document.getElementById('summary-output');
    const summaryText = document.getElementById('summary-text');
    const summarizeBtn = document.querySelector('.summarize-btn');
    const btnText = document.querySelector('.btn-text');
    const spinner = document.querySelector('.spinner');

    if (mode === 'text') {
        text = document.getElementById('blog-text').value;
    } else if (mode === 'url') {
        text = document.getElementById('extracted-content').textContent;
    } else if (mode === 'pdf') {
        text = document.getElementById('pdf-extracted-content').textContent;
    }

    if (!text.trim()) {
        summaryText.innerHTML = '<span style="color: #dc3545;">Please provide text, extract a URL, or upload a PDF first.</span>';
        summaryOutput.style.display = 'block';
        return;
    }

    summaryText.innerHTML = 'Summarizing...';
    summaryOutput.style.display = 'block';
    btnText.style.display = 'none';
    spinner.style.display = 'inline-block';
    try {
        const response = await fetch('http://127.0.0.1:8000/summarize/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const data = await response.json();
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
        if (response.ok) {
            summaryText.textContent = data.summary;
            history.push({
                mode,
                input: text,
                url: mode === 'url' ? document.getElementById('blog-url').value : null,
                summary: data.summary,
                timestamp: new Date().toLocaleString('en-US', { timeZone: 'Africa/Nairobi' })
            });
            updateHistory();
        } else {
            summaryText.innerHTML = `<span style="color: #dc3545;">API error: ${data.error}</span>`;
        }
    } catch (error) {
        btnText.style.display = 'inline';
        spinner.style.display = 'none';
        summaryText.innerHTML = `<span style="color: #dc3545;">Request failed: ${error.message}</span>`;
    }
}

// Initialize history and theme
updateHistory();