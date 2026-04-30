// frontend/src/services/websocket.js

class TaskWebSocket {
  constructor(taskId, onUpdate) {
    this.taskId = taskId;
    this.onUpdate = onUpdate;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnects = 5;
  }

  connect() {
    const base = process.env.REACT_APP_WS_URL || 'ws://127.0.0.1:8000';
    this.ws = new WebSocket(`${base}/ws/${this.taskId}`);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.onUpdate(data);
      } catch (e) { /* ignore parse errors */ }
    };

    this.ws.onclose = () => {
      if (this.reconnectAttempts < this.maxReconnects) {
        this.reconnectAttempts++;
        setTimeout(() => this.connect(), 2000 * this.reconnectAttempts);
      }
    };

    this.ws.onerror = () => {};
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export default TaskWebSocket;
