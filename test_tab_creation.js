/**
 * Simple test script to verify tab creation via Socket.IO
 */

const { io } = require('socket.io-client');

console.log('🧪 Testing tab creation...');

const socket = io('http://localhost:57575', {
  transports: ['websocket', 'polling'],
  timeout: 10000
});

socket.on('connect', () => {
  console.log('✅ Connected to server:', socket.id);
  
  // Listen for tab creation response
  socket.on('workspace:tab:created', (data) => {
    console.log('✅ Tab created successfully:', data);
    process.exit(0);
  });
  
  socket.on('workspace:tab:error', (data) => {
    console.log('❌ Tab creation error:', data);
    process.exit(1);
  });
  
  // Send tab creation request
  setTimeout(() => {
    console.log('📤 Sending tab creation request...');
    socket.emit('workspace:tab:create', {
      title: 'Test Tab',
      type: 'terminal',
      sessionId: 'test-session'
    });
  }, 1000);
});

socket.on('connect_error', (error) => {
  console.log('❌ Connection error:', error);
  process.exit(1);
});

socket.on('disconnect', (reason) => {
  console.log('🔌 Disconnected:', reason);
});

// Timeout after 15 seconds
setTimeout(() => {
  console.log('⏰ Test timeout - no response received');
  process.exit(1);
}, 15000);