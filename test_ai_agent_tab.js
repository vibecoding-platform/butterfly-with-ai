/**
 * Simple test script to verify AI agent tab creation and task assignment
 */

const { io } = require('socket.io-client');

console.log('🤖 Testing AI agent tab creation...');

const socket = io('http://localhost:57575', {
  transports: ['websocket', 'polling'],
  timeout: 10000
});

let tabId = null;

socket.on('connect', () => {
  console.log('✅ Connected to server:', socket.id);
  
  // Listen for tab creation response
  socket.on('workspace:tab:created', (data) => {
    console.log('✅ Tab created successfully:', data);
    
    if (data.tab && data.tab.type === 'ai_agent') {
      tabId = data.tab.id;
      console.log('🤖 AI Agent tab created:', tabId);
      
      // Test task assignment after tab creation
      setTimeout(() => testTaskAssignment(), 1000);
    }
  });
  
  // Listen for AI agent initialization
  socket.on('ai_agent:initialized', (data) => {
    console.log('🚀 AI Agent initialized:', data);
  });
  
  // Listen for task assignment response
  socket.on('ai_agent:task:assigned', (data) => {
    console.log('🎯 Task assigned successfully:', data);
  });
  
  socket.on('ai_agent:task:planning', (data) => {
    console.log('🧠 AI Agent planning:', data);
  });
  
  socket.on('ai_agent:task:error', (data) => {
    console.log('❌ AI Agent task error:', data);
  });
  
  // Send AI agent tab creation request
  setTimeout(() => {
    console.log('📤 Sending AI agent tab creation request...');
    socket.emit('workspace:tab:create', {
      title: 'AI Agent Test',
      type: 'ai_agent',
      agentType: 'autonomous',
      sessionId: 'test-session'
    });
  }, 1000);
});

function testTaskAssignment() {
  if (!tabId) {
    console.log('❌ No tab ID available for task assignment');
    return;
  }
  
  console.log('📤 Sending task assignment...');
  socket.emit('ai_agent:task:assign', {
    tabId: tabId,
    task: 'Deploy a simple web application',
    priority: 'high'
  });
}

socket.on('connect_error', (error) => {
  console.log('❌ Connection error:', error);
  process.exit(1);
});

socket.on('disconnect', (reason) => {
  console.log('🔌 Disconnected:', reason);
});

// Timeout after 20 seconds
setTimeout(() => {
  console.log('⏰ Test timeout - exiting');
  process.exit(0);
}, 20000);