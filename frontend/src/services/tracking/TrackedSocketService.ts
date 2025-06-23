/**
 * Tracked Socket Service
 * AetherTermServiceにSocket.IO connection trackingを統合
 */

import { io, Socket } from 'socket.io-client'
import { socketUrl } from '../../config/environment'
import { 
  SocketConnectionTracker, 
  NoOpSocketConnectionTracker 
} from './SocketConnectionTracker'
import type { 
  ISocketConnectionTracker, 
  SocketTrackingConfig 
} from './ISocketConnectionTracker'
import { getOpenObserveSink } from './OpenObserveSink'
import { getGrafanaCloudSink } from './GrafanaCloudSink'
import { 
  createB3TraceContext, 
  addTraceContextToSocketData,
  type B3TraceContext 
} from '../../utils/tracing'

interface VueTermWebSockets {
  shellWs: WebSocket | null
  ctlWs: WebSocket | null
}

export class TrackedSocketService {
  private socket: Socket | null = null
  private shellWs: WebSocket | null = null
  private ctlWs: WebSocket | null = null
  private static instance: TrackedSocketService
  private tracker: ISocketConnectionTracker

  private constructor(trackingConfig?: Partial<SocketTrackingConfig>) {
    // Initialize tracker based on configuration
    const isTrackingEnabled = import.meta.env.DEV || 
                            import.meta.env.VITE_SOCKET_TRACKING_ENABLED === 'true'
    
    if (isTrackingEnabled) {
      // Configure OpenObserve integration
      const config = {
        defaultTimeout: 5000,
        slowResponseThreshold: 1000,
        enableDetailedLogging: true,
        enableMetrics: true,
        ...trackingConfig
      }
      
      this.tracker = new SocketConnectionTracker(config)
      console.log('🔗 Socket tracking enabled with OpenObserve Cloud')
    } else {
      this.tracker = new NoOpSocketConnectionTracker()
      console.log('🔗 Socket tracking disabled')
    }
  }

  static getInstance(trackingConfig?: Partial<SocketTrackingConfig>): TrackedSocketService {
    if (!TrackedSocketService.instance) {
      TrackedSocketService.instance = new TrackedSocketService(trackingConfig)
    }
    return TrackedSocketService.instance
  }

  connect(): Socket {
    if (!this.socket) {
      this.socket = io(socketUrl || window.location.origin, {
        path: '/socket.io'
      })

      this.instrumentSocket(this.socket)
      this.setupEventListeners()
    }
    return this.socket
  }

  private instrumentSocket(socket: Socket): void {
    // Wrap emit method to track outgoing events
    const originalEmit = socket.emit.bind(socket)
    
    socket.emit = (...args: any[]) => {
      const [eventName, data, ...rest] = args
      
      // Create B3 trace context for this request
      const traceContext = createB3TraceContext()
      
      // Track the request
      const requestId = this.tracker.trackRequest(eventName, data || {})
      
      // Add both requestId and trace context to data
      let trackedData = data
      
      // Add trace context using B3 propagation
      trackedData = addTraceContextToSocketData(trackedData, traceContext)
      
      // Add requestId for tracking
      if (trackedData && typeof trackedData === 'object') {
        trackedData._requestId = requestId
      } else {
        trackedData = { 
          _originalData: trackedData,
          _requestId: requestId
        }
      }
      
      // Log trace correlation for debugging
      if (import.meta.env.DEV) {
        console.log(`🔗 Socket emit with trace: ${eventName}`, {
          requestId,
          traceId: traceContext.traceId.substring(0, 8) + '...',
          spanId: traceContext.spanId.substring(0, 8) + '...'
        })
      }
      
      // Call original emit with tracked data
      return originalEmit(eventName, trackedData, ...rest)
    }

    // Setup tracking callbacks
    this.tracker.onRequestTimeout((request) => {
      console.warn(`⏰ Socket request timeout: ${request.eventName}`, request)
    })

    this.tracker.onSlowResponse((request, duration) => {
      console.warn(`🐌 Slow socket response: ${request.eventName} (${duration}ms)`, request)
    })

    this.tracker.onError((request, error) => {
      console.error(`❌ Socket request error: ${request.eventName}`, { request, error })
    })
  }

  private setupEventListeners(): void {
    if (!this.socket) return

    this.socket.on('connect', () => {
      console.log('AetherTerm Socket.IO connected')
      this.tracker.trackResponse('socket:connect', { success: true })
      
      // Export connection status to observability sinks
      const openObserveSink = getOpenObserveSink()
      if (openObserveSink) {
        openObserveSink.exportConnectionStatus('connected', {
          'socket.id': this.socket?.id,
          'socket.url': window.location.origin
        })
      }
      
      const grafanaSink = getGrafanaCloudSink()
      if (grafanaSink) {
        grafanaSink.exportConnectionStatus('connected', {
          'socket.id': this.socket?.id,
          'socket.url': window.location.origin
        })
      }
      
      this.setupVueTermWebSockets()
    })

    this.socket.on('disconnect', (reason: string) => {
      console.log('AetherTerm Socket.IO disconnected')
      this.tracker.trackResponse('socket:disconnect', { reason })
      
      // Export disconnection status to observability sinks
      const openObserveSink = getOpenObserveSink()
      if (openObserveSink) {
        openObserveSink.exportConnectionStatus('disconnected', {
          'socket.disconnect.reason': reason,
          'socket.url': window.location.origin
        })
      }
      
      const grafanaSink = getGrafanaCloudSink()
      if (grafanaSink) {
        grafanaSink.exportConnectionStatus('disconnected', {
          'socket.disconnect.reason': reason,
          'socket.url': window.location.origin
        })
      }
      
      this.closeVueTermWebSockets()
    })

    this.socket.on('connect_error', (error: Error) => {
      console.error('AetherTerm Socket.IO connection error:', error)
      this.tracker.trackResponse('socket:connect_error', { error: error.message, success: false })
      
      // Export error status to observability sinks
      const openObserveSink = getOpenObserveSink()
      if (openObserveSink) {
        openObserveSink.exportConnectionStatus('error', {
          'socket.error.message': error.message,
          'socket.error.type': error.constructor.name,
          'socket.url': window.location.origin
        })
      }
      
      const grafanaSink = getGrafanaCloudSink()
      if (grafanaSink) {
        grafanaSink.exportConnectionStatus('error', {
          'socket.error.message': error.message,
          'socket.error.type': error.constructor.name,
          'socket.url': window.location.origin
        })
      }
    })

    // Track common terminal events
    this.setupTerminalEventTracking()
  }

  private setupTerminalEventTracking(): void {
    if (!this.socket) return

    const trackedEvents = [
      'terminal:created',
      'terminal:output',
      'shell:output',
      'terminal:error',
      'session:init',
      'session:end',
      'chat_message',
      'command_approval',
      'admin_pause_terminal',
      'admin_resume_terminal',
      'admin_suppress_output'
    ]

    trackedEvents.forEach(eventName => {
      this.socket!.on(eventName, (data: any) => {
        this.tracker.trackResponse(eventName, data, data?._requestId)
      })
    })
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

  getTracker(): ISocketConnectionTracker {
    return this.tracker
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.closeVueTermWebSockets()
  }

  // Terminal specific methods (using Socket.IO with tracking)
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

  // Terminal command methods (using Socket.IO with tracking)
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

  // Monitoring methods
  getConnectionMetrics() {
    return this.tracker.getMetrics()
  }

  getPendingRequests() {
    return this.tracker.getPendingRequests()
  }

  clearTrackingMetrics() {
    this.tracker.clearMetrics()
  }
}

export default TrackedSocketService