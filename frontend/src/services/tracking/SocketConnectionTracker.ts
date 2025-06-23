/**
 * Socket.IO Connection Tracker Implementation
 * Request-Response correlation tracking for Vue ↔ Python Socket.IO communication
 */

import type { 
  ISocketConnectionTracker, 
  PendingRequest, 
  ResponseInfo, 
  ConnectionMetrics, 
  EventMetrics,
  SocketTrackingConfig 
} from './ISocketConnectionTracker'
import { initializeOpenObserveSink, getOpenObserveSink } from './OpenObserveSink'
import { initializeGrafanaCloudSink, getGrafanaCloudSink } from './GrafanaCloudSink'

export class SocketConnectionTracker implements ISocketConnectionTracker {
  private pendingRequests = new Map<string, PendingRequest>()
  private responses: ResponseInfo[] = []
  private config: SocketTrackingConfig
  private requestCounter = 0
  
  // Event listeners
  private timeoutCallbacks: ((request: PendingRequest) => void)[] = []
  private slowResponseCallbacks: ((request: PendingRequest, duration: number) => void)[] = []
  private errorCallbacks: ((request: PendingRequest, error: string) => void)[] = []

  constructor(config: Partial<SocketTrackingConfig> = {}) {
    this.config = {
      defaultTimeout: 5000, // 5 seconds
      slowResponseThreshold: 1000, // 1 second
      maxPendingRequests: 100,
      enableDetailedLogging: true,
      enableMetrics: true,
      ...config
    }
    
    // Initialize observability sinks
    initializeOpenObserveSink()
    initializeGrafanaCloudSink()
    
    if (this.config.enableDetailedLogging) {
      console.log('🔗 Socket Connection Tracker initialized', this.config)
    }
  }

  trackRequest(eventName: string, data: any): string {
    const requestId = this.generateRequestId()
    const timestamp = Date.now()
    
    // Check max pending requests
    if (this.pendingRequests.size >= this.config.maxPendingRequests) {
      console.warn(`⚠️ Max pending requests reached (${this.config.maxPendingRequests})`)
      // Remove oldest pending request
      const oldestKey = this.pendingRequests.keys().next().value
      if (oldestKey) {
        this.pendingRequests.delete(oldestKey)
      }
    }
    
    const request: PendingRequest = {
      requestId,
      eventName,
      timestamp,
      data: this.sanitizeData(data),
      timeout: this.config.defaultTimeout
    }
    
    this.pendingRequests.set(requestId, request)
    
    // Set timeout
    setTimeout(() => {
      if (this.pendingRequests.has(requestId)) {
        this.trackTimeout(requestId)
      }
    }, this.config.defaultTimeout)
    
    if (this.config.enableDetailedLogging) {
      console.log(`📤 Socket request tracked: ${eventName}`, { requestId, timestamp })
    }
    
    return requestId
  }

  trackResponse(eventName: string, data: any, requestId?: string): void {
    const timestamp = Date.now()
    
    // Try to find corresponding request
    let matchedRequest: PendingRequest | undefined
    
    if (requestId && this.pendingRequests.has(requestId)) {
      matchedRequest = this.pendingRequests.get(requestId)
    } else {
      // Try to match by event name pattern
      matchedRequest = this.findMatchingRequest(eventName, data)
    }
    
    if (matchedRequest) {
      const duration = timestamp - matchedRequest.timestamp
      const success = !data.error && data.success !== false
      
      const response: ResponseInfo = {
        requestId: matchedRequest.requestId,
        responseEvent: eventName,
        duration,
        success,
        error: data.error || (!success ? 'Unknown error' : undefined),
        timestamp
      }
      
      this.responses.push(response)
      this.pendingRequests.delete(matchedRequest.requestId)
      
      // Export to observability sinks
      const openObserveSink = getOpenObserveSink()
      if (openObserveSink) {
        openObserveSink.exportRequestResponse(
          matchedRequest.eventName,
          eventName,
          duration,
          success,
          response.error,
          {
            'socket.request.id': matchedRequest.requestId,
            'socket.request.timestamp': matchedRequest.timestamp,
            'socket.response.timestamp': timestamp
          }
        )
      }
      
      const grafanaSink = getGrafanaCloudSink()
      if (grafanaSink) {
        grafanaSink.exportRequestResponse(
          matchedRequest.eventName,
          eventName,
          duration,
          success,
          response.error,
          {
            'socket.request.id': matchedRequest.requestId,
            'socket.request.timestamp': matchedRequest.timestamp,
            'socket.response.timestamp': timestamp
          }
        )
      }
      
      // Check for slow response
      if (duration > this.config.slowResponseThreshold) {
        this.slowResponseCallbacks.forEach(callback => {
          try {
            callback(matchedRequest!, duration)
          } catch (error) {
            console.error('Error in slow response callback:', error)
          }
        })
      }
      
      // Check for error
      if (!success && response.error) {
        this.errorCallbacks.forEach(callback => {
          try {
            callback(matchedRequest!, response.error!)
          } catch (error) {
            console.error('Error in error callback:', error)
          }
        })
      }
      
      if (this.config.enableDetailedLogging) {
        const status = success ? '✅' : '❌'
        console.log(`📥 Socket response tracked: ${eventName} ${status}`, { 
          requestId: matchedRequest.requestId, 
          duration: `${duration}ms`,
          success
        })
      }
    } else {
      if (this.config.enableDetailedLogging) {
        console.log(`📥 Socket response (no matching request): ${eventName}`, { 
          timestamp,
          dataKeys: Object.keys(data)
        })
      }
    }
  }

  trackTimeout(requestId: string): void {
    const request = this.pendingRequests.get(requestId)
    if (request) {
      this.pendingRequests.delete(requestId)
      
      // Export timeout to observability sinks
      const timeoutDuration = Date.now() - request.timestamp
      
      const openObserveSink = getOpenObserveSink()
      if (openObserveSink) {
        openObserveSink.exportTimeout(
          request.eventName,
          timeoutDuration,
          {
            'socket.request.id': requestId,
            'socket.request.timestamp': request.timestamp
          }
        )
      }
      
      const grafanaSink = getGrafanaCloudSink()
      if (grafanaSink) {
        grafanaSink.exportTimeout(
          request.eventName,
          timeoutDuration,
          {
            'socket.request.id': requestId,
            'socket.request.timestamp': request.timestamp
          }
        )
      }
      
      this.timeoutCallbacks.forEach(callback => {
        try {
          callback(request)
        } catch (error) {
          console.error('Error in timeout callback:', error)
        }
      })
      
      if (this.config.enableDetailedLogging) {
        console.warn(`⏰ Socket request timeout: ${request.eventName}`, { 
          requestId, 
          duration: `${Date.now() - request.timestamp}ms`
        })
      }
    }
  }

  trackError(requestId: string, error: Error | string): void {
    const request = this.pendingRequests.get(requestId)
    if (request) {
      const errorMessage = error instanceof Error ? error.message : error
      
      this.errorCallbacks.forEach(callback => {
        try {
          callback(request, errorMessage)
        } catch (err) {
          console.error('Error in error callback:', err)
        }
      })
      
      if (this.config.enableDetailedLogging) {
        console.error(`❌ Socket request error: ${request.eventName}`, { 
          requestId, 
          error: errorMessage
        })
      }
    }
  }

  getPendingRequests(): PendingRequest[] {
    return Array.from(this.pendingRequests.values())
  }

  getMetrics(): ConnectionMetrics {
    if (!this.config.enableMetrics) {
      return this.createEmptyMetrics()
    }
    
    const totalRequests = this.requestCounter
    const totalResponses = this.responses.length
    const timeoutCount = totalRequests - totalResponses - this.pendingRequests.size
    const errorCount = this.responses.filter(r => !r.success).length
    
    const responseTimes = this.responses.map(r => r.duration)
    const averageResponseTime = responseTimes.length > 0 
      ? responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length 
      : 0
    
    // Calculate event-specific metrics
    const eventMetrics = this.calculateEventMetrics()
    
    return {
      totalRequests,
      totalResponses,
      averageResponseTime,
      timeoutCount,
      errorCount,
      pendingCount: this.pendingRequests.size,
      eventMetrics
    }
  }

  clearMetrics(): void {
    this.responses = []
    this.requestCounter = 0
    
    if (this.config.enableDetailedLogging) {
      console.log('📊 Socket metrics cleared')
    }
  }

  onRequestTimeout(callback: (request: PendingRequest) => void): void {
    this.timeoutCallbacks.push(callback)
  }

  onSlowResponse(callback: (request: PendingRequest, duration: number) => void): void {
    this.slowResponseCallbacks.push(callback)
  }

  onError(callback: (request: PendingRequest, error: string) => void): void {
    this.errorCallbacks.push(callback)
  }

  // Private helper methods
  private generateRequestId(): string {
    this.requestCounter++
    return `req_${Date.now()}_${this.requestCounter}`
  }

  private sanitizeData(data: any): any {
    try {
      // Remove potentially sensitive data and large objects
      const sanitized = { ...data }
      delete sanitized.password
      delete sanitized.token
      delete sanitized.auth
      
      // Truncate large strings
      Object.keys(sanitized).forEach(key => {
        if (typeof sanitized[key] === 'string' && sanitized[key].length > 100) {
          sanitized[key] = sanitized[key].substring(0, 100) + '...'
        }
      })
      
      return sanitized
    } catch {
      return { _sanitized: true }
    }
  }

  private findMatchingRequest(eventName: string, data: any): PendingRequest | undefined {
    // Try to match by requestId in data
    if (data.requestId && this.pendingRequests.has(data.requestId)) {
      return this.pendingRequests.get(data.requestId)
    }
    
    // Try to match by event name pattern
    // e.g., 'terminal:create' -> 'terminal:created'
    const baseEventName = eventName.replace(/:(created|response|result|success|error)$/, '')
    
    for (const request of this.pendingRequests.values()) {
      if (request.eventName.startsWith(baseEventName)) {
        return request
      }
    }
    
    // If only one pending request, assume it's the match
    if (this.pendingRequests.size === 1) {
      return this.pendingRequests.values().next().value
    }
    
    return undefined
  }

  private calculateEventMetrics(): Map<string, EventMetrics> {
    const eventStats = new Map<string, {
      requests: PendingRequest[]
      responses: ResponseInfo[]
    }>()
    
    // Group by event name
    this.pendingRequests.forEach(request => {
      if (!eventStats.has(request.eventName)) {
        eventStats.set(request.eventName, { requests: [], responses: [] })
      }
      eventStats.get(request.eventName)!.requests.push(request)
    })
    
    this.responses.forEach(response => {
      const request = this.findRequestForResponse(response)
      if (request) {
        if (!eventStats.has(request.eventName)) {
          eventStats.set(request.eventName, { requests: [], responses: [] })
        }
        eventStats.get(request.eventName)!.responses.push(response)
      }
    })
    
    // Calculate metrics
    const metrics = new Map<string, EventMetrics>()
    
    eventStats.forEach((stats, eventName) => {
      const responseTimes = stats.responses.map(r => r.duration)
      const successCount = stats.responses.filter(r => r.success).length
      
      metrics.set(eventName, {
        eventName,
        requestCount: stats.requests.length + stats.responses.length,
        responseCount: stats.responses.length,
        averageTime: responseTimes.length > 0 
          ? responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length 
          : 0,
        minTime: responseTimes.length > 0 ? Math.min(...responseTimes) : 0,
        maxTime: responseTimes.length > 0 ? Math.max(...responseTimes) : 0,
        timeoutCount: stats.requests.length, // Current pending = potential timeouts
        errorCount: stats.responses.length - successCount,
        successRate: stats.responses.length > 0 ? successCount / stats.responses.length : 0
      })
    })
    
    return metrics
  }

  private findRequestForResponse(response: ResponseInfo): PendingRequest | undefined {
    // This is a simplified implementation
    // In practice, you'd maintain a mapping of response -> request
    return undefined
  }

  private createEmptyMetrics(): ConnectionMetrics {
    return {
      totalRequests: 0,
      totalResponses: 0,
      averageResponseTime: 0,
      timeoutCount: 0,
      errorCount: 0,
      pendingCount: 0,
      eventMetrics: new Map()
    }
  }
}

// Null Object Pattern implementation
export class NoOpSocketConnectionTracker implements ISocketConnectionTracker {
  trackRequest(): string { return 'noop' }
  trackResponse(): void {}
  trackTimeout(): void {}
  trackError(): void {}
  getPendingRequests(): PendingRequest[] { return [] }
  getMetrics(): ConnectionMetrics {
    return {
      totalRequests: 0,
      totalResponses: 0,
      averageResponseTime: 0,
      timeoutCount: 0,
      errorCount: 0,
      pendingCount: 0,
      eventMetrics: new Map()
    }
  }
  clearMetrics(): void {}
  onRequestTimeout(): void {}
  onSlowResponse(): void {}
  onError(): void {}
}