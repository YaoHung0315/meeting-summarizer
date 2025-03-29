document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const resultDiv = document.getElementById('result');

    // 拖放事件處理
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    dropZone.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFileSelect, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        dropZone.classList.add('dragover');
    }

    function unhighlight(e) {
        dropZone.classList.remove('dragover');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const file = dt.files[0];
        handleFile(file);
    }

    function handleFileSelect(e) {
        const file = e.target.files[0];
        handleFile(file);
    }

    function handleFile(file) {
        if (!file || !file.name.toLowerCase().endsWith('.mp3')) {
            alert('請上傳 MP3 格式的音訊檔案');
            return;
        }

        uploadFile(file);
    }

    async function uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);

        uploadStatus.classList.remove('d-none');
        resultDiv.classList.add('d-none');

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '上傳失敗');
            }

            const data = await response.json();
            displayResults(data);
            uploadStatus.classList.add('d-none');

        } catch (error) {
            console.error('Error:', error);
            alert('處理過程中發生錯誤：' + error.message);
            uploadStatus.classList.add('d-none');
        }
    }

    function displayResults(data) {
        resultDiv.classList.remove('d-none');
        document.querySelector('.summary-content').textContent = data.summary;
        document.querySelector('.action-plan-content').textContent = data.action_plan;
    }
});

function downloadSummary() {
    const summary = document.querySelector('.summary-content').textContent;
    const actionPlan = document.querySelector('.action-plan-content').textContent;
    const content = `音訊重點摘要：\n\n${summary}\n\n執行計劃：\n\n${actionPlan}`;
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '音訊摘要_' + new Date().toLocaleDateString('zh-TW').replace(/\//g, '-') + '.txt';
    
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    }, 100);
} 