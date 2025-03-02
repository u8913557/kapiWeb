// script.js
/**
 * 前端腳本，用於處理檔案上傳、截圖顯示和聊天功能。
 */

console.log('script.js 開始執行');

/**
 * 將訊息添加到聊天歷史。
 * @param {string} text - 訊息內容。
 * @param {string} sender - 發送者（'user' 或 'system'）。
 */
function addMessage(text, sender) {
  const messageDiv = document.createElement('div');
  messageDiv.textContent = text;
  messageDiv.className = sender === 'user' ? 'user-message' : 'system-message';
  const chatHistory = document.getElementById('chat-history');
  chatHistory.insertBefore(messageDiv, chatHistory.firstChild);
}

/**
 * 將檔案添加到檔案列表並綁定按鈕事件。
 * @param {string} filename - 檔案名稱。
 * @param {HTMLElement} fileList - 檔案列表容器。
 * @param {HTMLElement} screenshotContainer - 截圖顯示容器。
 * @param {HTMLElement} screenshotFilename - 截圖檔案名稱顯示元素。
 */
function addFileToList(filename, fileList, screenshotContainer, screenshotFilename) {
  const li = document.createElement('li');
  li.textContent = filename;
  li.dataset.filename = filename;

  // 移除按鈕
  const removeButton = document.createElement('button');
  removeButton.textContent = '移除';
  removeButton.className = 'remove-button';
  removeButton.addEventListener('click', async () => {
    console.log('刪除按鈕被點擊，檔案:', filename);
    if (!screenshotContainer || !screenshotFilename) {
      console.error('截圖區域元素未找到:', { screenshotContainer, screenshotFilename });
      return;
    }

    console.log('當前顯示檔案:', screenshotFilename.textContent);
    if (screenshotFilename.textContent === filename) {
      console.log('檔案匹配，清空中間區域');
      screenshotContainer.innerHTML = '';
      screenshotFilename.textContent = '';
    }

    try {
      const formData = new FormData();
      formData.append('filename', filename);
      const response = await fetch('/remove', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error('移除失敗');
      }
      fileList.removeChild(li);
    } catch (error) {
      console.error('移除檔案錯誤:', error);
    }
  });

  // 截圖按鈕
  const screenshotButton = document.createElement('button');
  screenshotButton.textContent = '截圖';
  screenshotButton.className = 'screenshot-button';
  screenshotButton.addEventListener('click', async () => {
    console.log('截圖按鈕被點擊，檔案:', filename);
    const fileExtension = filename.split('.').pop().toLowerCase();
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp'];

    screenshotContainer.innerHTML = '';
    screenshotFilename.textContent = filename;

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
          body: formData,
        });
        if (!response.ok) {
          throw new Error('截圖生成失敗');
        }
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

  // RAG 處理按鈕
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

  li.appendChild(removeButton);
  li.appendChild(screenshotButton);
  if (!li.classList.contains('rag-processed')) {
    li.appendChild(ragButton);
  }

  fileList.appendChild(li);
}

/**
 * 從後端載入檔案列表並顯示。
 * @param {HTMLElement} fileList - 檔案列表容器。
 * @param {HTMLElement} screenshotContainer - 截圖顯示容器。
 * @param {HTMLElement} screenshotFilename - 截圖檔案名稱顯示元素。
 */
async function loadFileList(fileList, screenshotContainer, screenshotFilename) {
  try {
    const response = await fetch('/files');
    if (!response.ok) {
      throw new Error('無法獲取檔案列表');
    }
    const data = await response.json();
    fileList.innerHTML = '';
    data.files.forEach(filename => addFileToList(filename, fileList, screenshotContainer, screenshotFilename));
  } catch (error) {
    console.error('獲取檔案列表時出錯:', error);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const fileUpload = document.getElementById('file-upload');
  const fileList = document.getElementById('file-list');
  const screenshotContainer = document.getElementById('screenshot-container');
  const screenshotFilename = document.getElementById('screenshot-filename');
  const chatInput = document.getElementById('chat-input');
  const sendButton = document.getElementById('send-button');
  const chatHistory = document.getElementById('chat-history');
  let chatId = null;

  if (!fileUpload || !fileList || !screenshotContainer || !screenshotFilename ||
      !chatInput || !sendButton || !chatHistory) {
    console.error('DOM 元素未找到');
    return;
  }

  loadFileList(fileList, screenshotContainer, screenshotFilename);

  fileUpload.addEventListener('change', async event => {
    const files = event.target.files;
    for (const file of files) {
      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/upload', {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) {
          throw new Error('Upload failed');
        }
        const data = await response.json();
        addFileToList(data.filename, fileList, screenshotContainer, screenshotFilename);
      } catch (error) {
        console.error('Error uploading file:', error);
      }
    }
  });

  sendButton.addEventListener('click', async () => {
    const message = chatInput.value.trim();
    if (!message) {
      return;
    }

    addMessage(message, 'user');
    chatInput.value = '';

    try {
      const formData = new FormData();
      formData.append('text', message);
      if (chatId) {
        formData.append('chat_id', chatId);
      }

      const response = await fetch('/chat-submit', {
        method: 'POST',
        body: formData,
      });
      if (!response.ok) {
        throw new Error('後端回應異常');
      }
      const data = await response.json();
      addMessage(data.result, 'system');
      chatId = data.chat_id;
    } catch (error) {
      console.error('錯誤:', error);
      addMessage('系統錯誤，請稍後再試。', 'system');
    }
  });
});
