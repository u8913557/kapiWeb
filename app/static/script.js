document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const fileList = document.getElementById('file-list');
    const screenshotImg = document.getElementById('screenshot-img');
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('send-button');
    const chatHistory = document.getElementById('chat-history');


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

                // 動態生成檔案名稱和操作按鈕
                const li = document.createElement('li');
                li.textContent = filename;
                li.dataset.filename = filename; // 儲存檔案名稱以便後續使用

                // 移除按鈕
                const removeButton = document.createElement('button');
                removeButton.textContent = '移除';
                removeButton.className = 'remove-button';
                removeButton.addEventListener('click', async () => {
                    const filename = li.dataset.filename;
                    const formData = new FormData();
                    formData.append('filename', filename);

                    try {
                        const response = await fetch('/remove', {
                            method: 'POST',
                            body: formData
                        });

                        if (!response.ok) {
                            throw new Error('Remove failed');
                        }

                        fileList.removeChild(li);
                    } catch (error) {
                        console.error('Error removing file:', error);
                    }
                });

                // RAG 處理按鈕
                const ragButton = document.createElement('button');
                ragButton.textContent = 'RAG 處理';
                ragButton.className = 'rag-button';
                ragButton.addEventListener('click', () => {
                    // 模擬 RAG 處理（待實作）
                    console.log('RAG 處理:', filename);
                    // 假設 RAG 處理完成，將檔案標記為已處理
                    li.classList.add('rag-processed');
                    li.removeChild(ragButton); // 移除 RAG 按鈕，只保留移除按鈕
                    const processedTag = document.createElement('span');
                    processedTag.textContent = ' (已 RAG 處理)';
                    processedTag.style.color = 'green';
                    li.appendChild(processedTag);
                });

                // 初始時顯示兩個按鈕
                if (!li.classList.contains('rag-processed')) {
                    li.appendChild(removeButton);
                    li.appendChild(ragButton);
                } else {
                    li.appendChild(removeButton); // 已 RAG 處理的檔案只顯示移除按鈕
                }

                fileList.appendChild(li);
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
