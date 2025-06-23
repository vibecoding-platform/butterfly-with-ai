/**
 * Socket.IO Connection Tracking Interface
 * Vue ↔ Python Socket.IO 連動確認用のトラッキングインターface
 */

export interface ISocketConnectionTracker {
  // Request-Response correlation tracking
  trackRequest(eventName: string, data: any): string // returns requestId
  trackResponse(eventName: string, data: any, requestId?: string): void
  trackTimeout(requestId: string): void
  trackError(requestId: string, error: Error | string): void
  
  // Real-time monitoring
  getPendingRequests(): PendingRequest[]
  getMetrics(): ConnectionMetrics
  clearMetrics(): void
  
  // Event listening
  onRequestTimeout(callback: (request: PendingRequest) => void): void
  onSlowResponse(callback: (request: PendingRequest, duration: number) => void): void
  onError(callback: (request: PendingRequest, error: string) => void): void
}

export interface PendingRequest {
  requestId: string
  eventName: string
  timestamp: number
  data: any
  timeout?: number
}

export interface ResponseInfo {
  requestId: string
  responseEvent: string
  duration: number
  success: boolean
  error?: string
  timestamp: number
}

export interface ConnectionMetrics {
  totalRequests: number
  totalResponses: number
  averageResponseTime: number
  timeoutCount: number
  errorCount: number
  pendingCount: number
  
  // Event-specific metrics
  eventMetrics: Map<string, EventMetrics>
}

export interface EventMetrics {
  eventName: string
  requestCount: number
  responseCount: number
  averageTime: number
  minTime: number
  maxTime: number
  timeoutCount: number
  errorCount: number
  successRate: number
}

// Configuration
export interface SocketTrackingConfig {
  defaultTimeout: number // milliseconds
  slowResponseThreshold: number // milliseconds
  maxPendingRequests: number
  enableDetailedLogging: boolean
  enableMetrics: boolean
}

// Service DI keys
export const SOCKET_TRACKER_KEY = Symbol('SocketConnectionTracker')
export const TRACKING_CONFIG_KEY = Symbol('SocketTrackingConfig')