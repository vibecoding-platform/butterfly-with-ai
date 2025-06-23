import { io, Socket } from 'socket.io-client'
import { socketUrl } from '../config/environment'

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
      this.socket = io(socketUrl || window.location.origin, {
        path: '/socket.io'
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
    // No need to create separate WebSocket connections for VueTerm
    // VueTerm will use the existing Socket.IO connection
    console.log('VueTerm using Socket.IO')
  }

  private closeVueTermWebSockets(): void {
    // No need to close separate WebSocket connections
  }

  getSocket(): Socket | null {
    return this.socket
  }


  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.closeVueTermWebSockets()
  }

  // Terminal specific methods (using Socket.IO)
  // onShellOutput(callback: (data: string) => void): void {
  //   if (this.socket) {
  //     this.socket.on('shell_output', callback)
  //   }
  // }

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
      console.log('Sending command:', command) // Debug log
      
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