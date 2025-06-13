<template>
  <div class="terminal-container">
    <!-- Connection Status -->
    <div v-if="!terminalStore.connectionState.isConnected" class="connection-status">
      <div class="status-indicator" :class="connectionStatusClass">
        {{ connectionStatusText }}
      </div>
      <div v-if="terminalStore.connectionState.isReconnecting" class="reconnect-info">
        Reconnection attempt:
        {{
          terminalStore.connectionState.reconnectAttempts
        }}/{{ terminalStore.connectionState.maxReconnectAttempts }}
      </div>
    </div>

    <!-- Terminal Blocked Overlay -->

    <div v-if="terminalStore.isTerminalBlocked" class="terminal-overlay">
      <div class="overlay-content">
        <div v-if="terminalStore.session.isPaused" class="block-reason">
          <h3>Terminal Paused</h3>
          <p>Terminal has been paused by administrator</p>
        </div>

        <div v-else-if="terminalStore.hasPendingCommands" class="block-reason">
          <h3>Commands Pending Review</h3>
          <p>{{ terminalStore.pendingCommands.length }} command(s) awaiting approval</p>
          <div class="pending-commands">
            <div v-for="cmd in terminalStore.pendingCommands" :key="cmd.id" class="pending-command">
              <code>{{ cmd.command }}</code>
              <span class="risk-level" :class="cmd.riskLevel">{{ cmd.riskLevel }}</span>
            </div>
          </div>
        </div>
        <div v-else-if="terminalStore.isOutputSuppressed" class="block-reason">
          <h3>Output Suppressed</h3>
          <p>Terminal output is currently suppressed</p>
        </div>
        <div v-else-if="!terminalStore.connectionState.isConnected" class="block-reason">
          <h3>Connection Lost</h3>
          <p>Reconnecting to terminal service...</p>
        </div>
      </div>
    </div>


    <!-- Xterm.js Integration -->
    <div id="terminal" class="xterm-container">
      <div v-if="isAdministratorLocked" class="admin-lock-warning">
        Administrator Locked
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { FitAddon } from '@xterm/addon-fit';
import { Unicode11Addon } from '@xterm/addon-unicode11';
import { WebLinksAddon } from '@xterm/addon-web-links';
import { Terminal, type ITheme } from '@xterm/xterm';
import '@xterm/xterm/css/xterm.css';
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useAetherTerminalServiceStore } from '../stores/aetherTerminalServiceStore';

const terminalEl = ref<HTMLElement | null>(null);
const terminal = ref<Terminal | null>(null);
const fitAddon = ref<FitAddon | null>(null);

const terminalStore = useAetherTerminalServiceStore();

const isAdministratorLocked = computed(() => {
  return terminalStore.isAdministratorLocked;
});

// Connection status computed properties
const connectionStatusClass = computed(() => {
  switch (terminalStore.connectionStatus) {
    case 'connected':
      return 'status-connected';
    case 'connecting':
      return 'status-connecting';
    case 'reconnecting':
      return 'status-reconnecting';
    default:
      return 'status-disconnected';
  }
});

const connectionStatusText = computed(() => {
  switch (terminalStore.connectionStatus) {
    case 'connected':
      return 'Connected';
    case 'connecting':
      return 'Connecting...';
    case 'reconnecting':
      return 'Reconnecting...';
    default:
      return 'Disconnected';
  }
});

const theme: ITheme = {
  background: '#1e1e1e',
  foreground: '#ffffff',
  cursor: '#ffffff',
  cursorAccent: '#000000',
  selectionBackground: 'rgba(255, 255, 255, 0.3)',
  selectionForeground: '#000000',
  black: '#000000',
  red: '#cd3131',
  green: '#0dbc79',
  yellow: '#e5e510',
  blue: '#3b78ff',
  magenta: '#bc3fbc',
  cyan: '#0dc2c2',
  white: '#e5e5e5',
  brightBlack: '#666666',
  brightRed: '#f14c4c',
  brightGreen: '#23d18b',
  brightYellow: '#f5f543',
  brightBlue: '#3b8eea',
  brightMagenta: '#d670d6',
  brightCyan: '#29b8db',
  brightWhite: '#ffffff'
};

onMounted(async () => {
  await terminalStore.connect();

  terminalEl.value = document.getElementById('terminal');
  if (terminalEl.value) {
    terminal.value = new Terminal({
      convertEol: true,
      cursorBlink: true,
      disableStdin: false,
      scrollback: 1000,
      theme: theme,
      allowProposedApi: true,
    });

    fitAddon.value = new FitAddon();
    terminal.value.loadAddon(fitAddon.value);

    const webLinksAddon = new WebLinksAddon();
    terminal.value.loadAddon(webLinksAddon);

    const unicode11Addon = new Unicode11Addon();
    terminal.value.loadAddon(unicode11Addon);
    //unicode11Addon.loadWebFont().then(() => {
    terminal.value?.refresh(0, terminal.value.rows - 1);
    //});

    terminal.value.open(terminalEl.value);
    fitAddon.value.fit();

    // Connect to the socket and receive data
    terminalStore.onShellOutput((data: string) => {
      console.log('onShellOutput called with:', data);
      terminal.value?.write(data);
    });

    terminal.value.onKey(e => {
      const ev = e.domEvent;

      if (isAdministratorLocked.value) {
        ev.preventDefault();
        return;
      }

      const printable = !ev.altKey && !ev.ctrlKey && !ev.metaKey;

      if (terminal.value) {
        if (ev.keyCode === 13) {
          // Enter key
          sendCommand(terminal.value.getSelection() || '');
          terminal.value.write('\r\n');
        } else if (ev.keyCode === 8) {
          // Backspace key
          // Do not delete if the line is empty
          if (terminal.value.buffer.active.cursorX > 0) {
            terminal.value.write('\b \b');
          }
        } else if (printable) {
          terminal.value.write(e.key);
        }
      }
    });

    window.addEventListener('resize', () => {
      fitAddon.value?.fit();
    });
  }
});

onUnmounted(() => {
  terminalStore.offShellOutput();
  terminal.value?.dispose();
  window.removeEventListener('resize', () => {
    fitAddon.value?.fit();
  });
});

// Send commands to the backend
const sendCommand = (command: string) => {
  terminalStore.submitCommand(command);
};

// Override WebSocket.send to log data
// const originalSend = WebSocket.prototype.send
// const originalSend = function(data) {
//   console.log('Sending data:', data) // Debug log
//   originalSend.apply(this, [
// }
</script>

<style scoped>
.terminal-container {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: #1e1e1e;
  color: #ffffff;
  font-family: 'Courier New', monospace;
  position: relative;
}

.connection-status {
  padding: 8px 12px;
  background-color: #2d2d2d;
  border-bottom: 1px solid #444;
}

.status-indicator {
  font-size: 12px;
  font-weight: bold;
}

.status-connected {
  color: #4caf50;
}

.status-connecting {
  color: #ff9800;
}

.status-reconnecting {
  color: #ff9800;
}

.status-disconnected {
  color: #f44336;
}

.reconnect-info {
  font-size: 11px;
  color: #ccc;
  margin-top: 4px;
}

.terminal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}

.overlay-content {
  background-color: #2d2d2d;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
  max-width: 400px;
}

.block-reason h3 {
  margin: 0 0 10px 0;
  color: #ff9800;
}

.pending-commands {
  margin-top: 15px;
  text-align: left;
}

.pending-command {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background-color: #1e1e1e;
  margin: 4px 0;
  border-radius: 4px;
}

.pending-command code {
  color: #4caf50;
}

.risk-level {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: bold;
}

.risk-level.low {
  background-color: #4caf50;
}

.risk-level.medium {
  background-color: #ff9800;
}

.risk-level.high {
  background-color: #ff5722;
}

.risk-level.critical {
  background-color: #f44336;
}

.xterm-container {
  flex: 1;
  /* Take up remaining space */
  border-top: 1px solid #444;
}

.admin-lock-warning {
  position: absolute;
  top: 10px;
  right: 10px;
  background-color: red;
  color: white;
  padding: 5px;
  border-radius: 5px;
  font-weight: bold;
  z-index: 20;
}
</style>