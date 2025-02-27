document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const fileList = document.getElementById('file-list');
    const screenshotContainer = document.getElementById('screenshot-container');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatHistory = document.getElementById('chat-history');

    // 提取按鈕生成邏輯為獨立函式
    function addFileToList(filename) {
        const li = document.createElement('li');
        li.textContent = filename;
        li.dataset.filename = filename; // 儲存檔案名稱以便後續使用

        // 「移除」按鈕
        const removeButton = document.createElement('button');
        removeButton.textContent = '移除';
        removeButton.className = 'remove-button';
        removeButton.addEventListener('click', async () => {
            const formData = new FormData();
            formData.append('filename', filename);
            try {
                const response = await fetch('/remove', {
                    method: 'POST',
                    body: formData
                });
                if (!response.ok) throw new Error('Remove failed');
                fileList.removeChild(li);
            } catch (error) {
                console.error('Error removing file:', error);
            }
        });

        // 「截圖」按鈕
        const screenshotButton = document.createElement('button');
        screenshotButton.textContent = '截圖';
        screenshotButton.className = 'screenshot-button';
        screenshotButton.addEventListener('click', async () => {
            console.log('截圖按鈕被點擊，檔案:', filename);
            const fileExtension = filename.split('.').pop().toLowerCase();
            const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp'];
            const screenshotFilename = document.getElementById('screenshot-filename');
        
            // 清空中間區域並更新檔案名稱
            screenshotContainer.innerHTML = '';
            screenshotFilename.textContent = filename; // 顯示檔案名稱
        
            if (imageExtensions.includes(fileExtension)) {
                const img = document.createElement('img');
                img.src = `/uploads/${filename}`;
                img.alt = filename;
                img.style.display = 'block';
                screenshotContainer.appendChild(img);
            } else if (fileExtension === 'pdf') {
                const formData = new FormData();
                formData.append('file_path', filename);
                try {
                    const response = await fetch('/screenshot', {
                        method: 'POST',
                        body: formData
                    });
                    if (!response.ok) throw new Error('截圖生成失敗');
                    const data = await response.json();
                    data.thumbnails.forEach(thumb => {
                        const img = document.createElement('img');
                        img.src = thumb;
                        img.alt = `Page of ${filename}`;
                        img.style.display = 'block';
                        screenshotContainer.appendChild(img);
                    });
                } catch (error) {
                    console.error('截圖錯誤:', error);
                    const img = document.createElement('img');
                    img.src = '/static/default-preview.png';
                    screenshotContainer.appendChild(img);
                }
            } else {
                const img = document.createElement('img');
                img.src = '/static/default-preview.png';
                screenshotContainer.appendChild(img);
            }
        });

        // 「RAG 處理」按鈕
        const ragButton = document.createElement('button');
        ragButton.textContent = 'RAG 處理';
        ragButton.className = 'rag-button';
        ragButton.addEventListener('click', () => {
            console.log('RAG 處理:', filename);
            li.classList.add('rag-processed');
            li.removeChild(ragButton);
            const processedTag = document.createElement('span');
            processedTag.textContent = ' (已 RAG 處理)';
            processedTag.style.color = 'green';
            li.appendChild(processedTag);
        });

        // 添加按鈕到 li
        li.appendChild(removeButton);
        li.appendChild(screenshotButton);
        if (!li.classList.contains('rag-processed')) {
            li.appendChild(ragButton);
        }

        fileList.appendChild(li);
    }

    // 刷新時載入檔案列表
    async function loadFileList() {
        try {
            const response = await fetch('/files');
            if (!response.ok) throw new Error('無法獲取檔案列表');
            const data = await response.json();
            const files = data.files;

            // 清空現有列表
            fileList.innerHTML = '';

            // 動態生成檔案列表並添加按鈕
            files.forEach(filename => {
                addFileToList(filename); // 使用統一的函式添加檔案
            });
        } catch (error) {
            console.error('獲取檔案列表時出錯:', error);
        }
    }

    // 調用刷新函式
    loadFileList();


    // 處理檔案上傳
    fileUpload.addEventListener('change', async (event) => {
        const files = event.target.files;
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                // 發送上傳請求到後端
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('Upload failed');
                }

                const data = await response.json();
                const filename = data.filename;
                addFileToList(filename);
                
            } catch (error) {
                console.error('Error uploading file:', error);
            }
        }
    });
    
    // 添加訊息到對話歷史的函數
    function addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.textContent = text;
        messageDiv.className = sender === 'user' ? 'user-message' : 'system-message';
        chatHistory.insertBefore(messageDiv, chatHistory.firstChild); // 插入到最前面
    }

    // 發送按鈕的事件監聽器
    sendButton.addEventListener('click', async () => {
        const message = chatInput.value.trim();
        if (message) {
            // 1. 將用戶的訊息添加到聊天歷史中
            addMessage(message, 'user');
            chatInput.value = ''; // 清空輸入框

            // 2. 將訊息發送到後端並接收回應
            try {
                const formData = new FormData();
                formData.append('text', message);

                const response = await fetch('/chat-submit', {
                    method: 'POST',
                    body: formData
                });

                if (!response.ok) {
                    throw new Error('後端回應異常');
                }

                const data = await response.json();

                // 3. 將後端的回應添加到聊天歷史中
                addMessage(data.result, 'system');
            } catch (error) {
                console.error('錯誤:', error);
                addMessage('系統錯誤，請稍後再試。', 'system');
            }
        }
    });
});
