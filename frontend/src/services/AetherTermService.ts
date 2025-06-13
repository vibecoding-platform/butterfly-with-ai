import { io, Socket } from 'socket.io-client'
import { getSocketPath, getSocketUrl } from '../config/environment'

interface VueTermWebSockets {
  shellWs: WebSocket | null
  ctlWs: WebSocket | null
}

class AetherTermService {
  private socket: Socket | null = null
  private shellWs: WebSocket | null = null
  private ctlWs: WebSocket | null = null
  private static instance: AetherTermService

  private constructor() { }

  static getInstance(): AetherTermService {
    if (!AetherTermService.instance) {
      AetherTermService.instance = new AetherTermService()
    }
    return AetherTermService.instance
  }

  connect(): Socket {
    if (!this.socket) {
      this.socket = io(getSocketUrl(), {
        path: getSocketPath()
      })

      this.socket.on('connect', () => {
        console.log('AetherTerm Socket.IO connected')
        this.setupVueTermWebSockets()
      })

      this.socket.on('disconnect', () => {
        console.log('AetherTerm Socket.IO disconnected')
        this.closeVueTermWebSockets()
      })
    }
    return this.socket
  }

  private setupVueTermWebSockets(): void {
    // Create WebSocket connections for VueTerm integration
    const baseUrl = getSocketUrl().replace(/^http/, 'ws')

    if (!this.shellWs) {
      this.shellWs = new WebSocket(`${baseUrl}/shell`)
      this.shellWs.onopen = () => console.log('VueTerm Shell WebSocket connected')
      this.shellWs.onclose = () => console.log('VueTerm Shell WebSocket disconnected')
      this.shellWs.onerror = (error) => console.error('VueTerm Shell WebSocket error:', error)
    }

    if (!this.ctlWs) {
      this.ctlWs = new WebSocket(`${baseUrl}/ctl`)
      this.ctlWs.onopen = () => console.log('VueTerm Control WebSocket connected')
      this.ctlWs.onclose = () => console.log('VueTerm Control WebSocket disconnected')
      this.ctlWs.onerror = (error) => console.error('VueTerm Control WebSocket error:', error)
    }
  }

  private closeVueTermWebSockets(): void {
    if (this.shellWs) {
      this.shellWs.close()
      this.shellWs = null
    }
    if (this.ctlWs) {
      this.ctlWs.close()
      this.ctlWs = null
    }
  }

  getSocket(): Socket | null {
    return this.socket
  }

  getVueTermWebSockets(): VueTermWebSockets {
    return {
      shellWs: this.shellWs,
      ctlWs: this.ctlWs
    }
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.closeVueTermWebSockets()
  }

  // Terminal specific methods (using Socket.IO)
  onShellOutput(callback: (data: string) => void): void {
    if (this.socket) {
      this.socket.on('shell_output', callback)
    }
  }

  onControlOutput(callback: (data: string) => void): void {
    if (this.socket) {
      this.socket.on('ctl_output', callback)
    }
  }

  // Connection event methods
  onConnect(callback: () => void): void {
    if (this.socket) {
      this.socket.on('connect', callback)
    }
  }

  onDisconnect(callback: () => void): void {
    if (this.socket) {
      this.socket.on('disconnect', callback)
    }
  }

  onError(callback: (error: any) => void): void {
    if (this.socket) {
      this.socket.on('connect_error', callback)
    }
  }

  // Chat specific methods (using Socket.IO)
  onChatMessage(callback: (data: any) => void): void {
    if (this.socket) {
      this.socket.on('chat_message', callback)
    }
  }

  sendChatMessage(message: any): void {
    if (this.socket) {
      this.socket.emit('chat_message', message)
    }
  }

  // Terminal command methods (using Socket.IO)
  sendCommand(command: string, commandId?: string): void {
    if (this.socket) {
      this.socket.emit('terminal_command', {
        command: command,
        commandId: commandId || Date.now().toString()
      })
    }
  }

  // Admin control methods (using Socket.IO)
  onAdminPauseTerminal(callback: (data: { reason: string }) => void): void {
    if (this.socket) {
      this.socket.on('admin_pause_terminal', callback)
    }
  }

  onAdminResumeTerminal(callback: () => void): void {
    if (this.socket) {
      this.socket.on('admin_resume_terminal', callback)
    }
  }

  onAdminSuppressOutput(callback: (data: { suppress: boolean, reason?: string }) => void): void {
    if (this.socket) {
      this.socket.on('admin_suppress_output', callback)
    }
  }

  onCommandApproval(callback: (data: { commandId: string, approved: boolean, reason?: string }) => void): void {
    if (this.socket) {
      this.socket.on('command_approval', callback)
    }
  }

  // Emit command review required
  emitCommandReviewRequired(data: { commandId: string, command: string, riskLevel: string, aiSuggestion: string }): void {
    if (this.socket) {
      this.socket.emit('command_review_required', data)
    }
  }

  // Cleanup methods
  offShellOutput(callback?: (data: string) => void): void {
    if (this.socket) {
      this.socket.off('shell_output', callback)
    }
  }

  offControlOutput(callback?: (data: string) => void): void {
    if (this.socket) {
      this.socket.off('ctl_output', callback)
    }
  }

  offChatMessage(callback?: (data: any) => void): void {
    if (this.socket) {
      this.socket.off('chat_message', callback)
    }
  }

  offConnect(callback?: () => void): void {
    if (this.socket) {
      this.socket.off('connect', callback)
    }
  }

  offDisconnect(callback?: () => void): void {
    if (this.socket) {
      this.socket.off('disconnect', callback)
    }
  }

  offError(callback?: (error: any) => void): void {
    if (this.socket) {
      this.socket.off('connect_error', callback)
    }
  }
}

export default AetherTermService