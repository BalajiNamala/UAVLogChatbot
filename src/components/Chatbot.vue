<template>
  <div class="chatbot">
    <div class="chat-window">
      <div
        v-for="(msg, index) in chatHistory"
        :key="index"
        :class="['message', msg.from]"
      >
        <strong>{{ msg.from === 'user' ? 'You' : 'Bot' }}:</strong> {{ msg.text }}
      </div>
    </div>
    <div class="chat-input">
      <input
        v-model="userInput"
        @keyup.enter="askQuestion"
        placeholder="Ask UAV Chatbot..."
      />
      <button @click="askQuestion">Send</button>
    </div>
  </div>
</template>

<script>
export default {
  data () {
    return {
      userInput: '',
      chatHistory: []
    }
  },
  methods: {
    async askQuestion () {
      if (!this.userInput.trim()) return

      const payload = {
        question: this.userInput
      }

      try {
        const response = await fetch('http://localhost:8000/api/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        })

        const data = await response.json()

        this.chatHistory.push({ from: 'user', text: this.userInput })
        this.chatHistory.push({ from: 'bot', text: data.response })
        this.userInput = ''
      } catch (err) {
        console.error('Chat request failed:', err)
        this.chatHistory.push({ from: 'bot', text: 'Error communicating with server.' })
      }
    }
  }
}
</script>

<style scoped>
.chatbot {
  width: 400px;
  height: 300px;
  background: white;
  border: 1px solid #ccc;
  border-radius: 10px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  font-family: sans-serif;
}

.chat-window {
  flex: 1;
  padding: 10px;
  overflow-y: auto;
  background: #f5f5f5;
}

.chat-input {
  display: flex;
  border-top: 1px solid #ddd;
  padding: 10px;
  background: #fff;
}

.chat-input input {
  flex: 1;
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

.chat-input button {
  margin-left: 8px;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.message {
  margin-bottom: 8px;
}

.message.user {
  text-align: right;
  color: blue;
}

.message.bot {
  text-align: left;
  color: green;
}
</style>
