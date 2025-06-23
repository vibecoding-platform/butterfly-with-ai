/**
 * OpenObserve Cloud Sink
 * Socket.IO tracking data sink to OpenObserve Cloud
 */

export interface OpenObserveConfig {
  endpoint: string
  organization: string
  username: string
  password: string
  streamName?: string
}

export interface SocketTraceEvent {
  timestamp: number
  traceId: string
  spanId: string
  operationName: string
  duration?: number
  tags: Record<string, any>
  status: 'ok' | 'error' | 'timeout'
  level: 'info' | 'warn' | 'error'
}

// OTLP-compliant trace data structure
export interface OTLPSpan {
  traceId: string
  spanId: string
  parentSpanId?: string
  name: string
  kind: number
  startTimeUnixNano: string
  endTimeUnixNano: string
  attributes: Array<{
    key: string
    value: {
      stringValue?: string
      intValue?: string
      doubleValue?: number
      boolValue?: boolean
    }
  }>
  status: {
    code: number
    message?: string
  }
}

export interface OTLPTraceData {
  resourceSpans: Array<{
    resource: {
      attributes: Array<{
        key: string
        value: {
          stringValue?: string
          intValue?: string
          doubleValue?: number
          boolValue?: boolean
        }
      }>
    }
    instrumentationLibrarySpans: Array<{
      instrumentationLibrary: {
        name: string
        version: string
      }
      spans: OTLPSpan[]
    }>
  }>
}

export class OpenObserveSink {
  private config: OpenObserveConfig
  private batchSize = 10
  private flushInterval = 5000 // 5 seconds
  private batch: SocketTraceEvent[] = []
  private flushTimer: number | null = null

  constructor(config: OpenObserveConfig) {
    this.config = {
      streamName: 'socket-io-traces',
      ...config
    }

    console.log('📊 OpenObserve Sink initialized', {
      endpoint: this.config.endpoint,
      organization: this.config.organization,
      streamName: this.config.streamName
    })

    // Start periodic flush
    this.startPeriodicFlush()
  }

  /**
   * Export socket trace event to OpenObserve
   */
  public exportTrace(event: SocketTraceEvent): void {
    // Add to batch
    this.batch.push(event)

    // Flush if batch is full
    if (this.batch.length >= this.batchSize) {
      this.flush()
    }
  }

  /**
   * Export request-response correlation
   */
  public exportRequestResponse(
    requestEvent: string,
    responseEvent: string,
    duration: number,
    success: boolean,
    error?: string,
    metadata?: Record<string, any>
  ): void {
    const traceEvent: SocketTraceEvent = {
      timestamp: Date.now(),
      traceId: this.generateTraceId(),
      spanId: this.generateSpanId(),
      operationName: `${requestEvent} -> ${responseEvent}`,
      duration,
      tags: {
        'socket.request.event': requestEvent,
        'socket.response.event': responseEvent,
        'socket.success': success,
        'socket.error': error || null,
        'service.name': 'aetherterm-frontend',
        'service.version': '1.0.0',
        ...metadata
      },
      status: error ? 'error' : (success ? 'ok' : 'timeout'),
      level: error ? 'error' : (duration > 1000 ? 'warn' : 'info')
    }

    this.exportTrace(traceEvent)
  }

  /**
   * Export socket connection status
   */
  public exportConnectionStatus(
    status: 'connected' | 'disconnected' | 'error',
    metadata?: Record<string, any>
  ): void {
    const traceEvent: SocketTraceEvent = {
      timestamp: Date.now(),
      traceId: this.generateTraceId(),
      spanId: this.generateSpanId(),
      operationName: `socket.${status}`,
      tags: {
        'socket.connection.status': status,
        'service.name': 'aetherterm-frontend',
        'socket.url': window.location.origin,
        ...metadata
      },
      status: status === 'error' ? 'error' : 'ok',
      level: status === 'error' ? 'error' : 'info'
    }

    this.exportTrace(traceEvent)
  }

  /**
   * Export timeout event
   */
  public exportTimeout(
    requestEvent: string,
    timeoutDuration: number,
    metadata?: Record<string, any>
  ): void {
    const traceEvent: SocketTraceEvent = {
      timestamp: Date.now(),
      traceId: this.generateTraceId(),
      spanId: this.generateSpanId(),
      operationName: `${requestEvent} [TIMEOUT]`,
      duration: timeoutDuration,
      tags: {
        'socket.request.event': requestEvent,
        'socket.timeout.duration': timeoutDuration,
        'socket.error': 'Request timeout',
        'service.name': 'aetherterm-frontend',
        ...metadata
      },
      status: 'timeout',
      level: 'warn'
    }

    this.exportTrace(traceEvent)
  }

  /**
   * Convert SocketTraceEvent to OTLP format
   */
  private convertToOTLP(events: SocketTraceEvent[]): OTLPTraceData {
    const spans: OTLPSpan[] = events.map(event => {
      const startTime = event.timestamp * 1000000 // Convert to nanoseconds
      const endTime = event.duration ? startTime + (event.duration * 1000000) : startTime
      
      return {
        traceId: event.traceId,
        spanId: event.spanId,
        name: event.operationName,
        kind: 1, // SPAN_KIND_CLIENT
        startTimeUnixNano: startTime.toString(),
        endTimeUnixNano: endTime.toString(),
        attributes: Object.entries(event.tags).map(([key, value]) => ({
          key,
          value: this.convertAttributeValue(value)
        })),
        status: {
          code: event.status === 'ok' ? 1 : 2, // 1 = OK, 2 = ERROR
          message: event.status === 'error' ? event.tags.error : undefined
        }
      }
    })

    return {
      resourceSpans: [{
        resource: {
          attributes: [
            {
              key: 'service.name',
              value: { stringValue: 'aetherterm-frontend' }
            },
            {
              key: 'service.version',
              value: { stringValue: '1.0.0' }
            },
            {
              key: 'telemetry.sdk.name',
              value: { stringValue: 'aetherterm-socket-tracing' }
            },
            {
              key: 'telemetry.sdk.version',
              value: { stringValue: '1.0.0' }
            }
          ]
        },
        instrumentationLibrarySpans: [{
          instrumentationLibrary: {
            name: 'aetherterm-socket-io',
            version: '1.0.0'
          },
          spans
        }]
      }]
    }
  }

  /**
   * Convert JavaScript value to OTLP attribute value
   */
  private convertAttributeValue(value: any): { stringValue?: string; intValue?: string; doubleValue?: number; boolValue?: boolean } {
    if (typeof value === 'string') {
      return { stringValue: value }
    } else if (typeof value === 'number') {
      return Number.isInteger(value) ? { intValue: value.toString() } : { doubleValue: value }
    } else if (typeof value === 'boolean') {
      return { boolValue: value }
    } else {
      return { stringValue: JSON.stringify(value) }
    }
  }

  /**
   * Flush current batch to OpenObserve using OTLP format
   */
  public async flush(): Promise<void> {
    if (this.batch.length === 0) return

    const events = [...this.batch]
    this.batch = []

    try {
      // Convert to OTLP format
      const otlpData = this.convertToOTLP(events)

      // Send to OpenObserve OTLP traces endpoint
      const response = await fetch(`${this.config.endpoint}/v1/traces`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${btoa(`${this.config.username}:${this.config.password}`)}`,
          'Content-Type': 'application/json',
          'User-Agent': 'aetherterm-socket-tracing/1.0.0'
        },
        body: JSON.stringify(otlpData)
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Failed to export OTLP traces to OpenObserve:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText
        })
        
        // Fallback: Try legacy logs endpoint
        await this.flushLegacy(events)
      } else {
        console.log(`✅ Exported ${events.length} OTLP traces to OpenObserve Cloud`)
      }

    } catch (error) {
      console.error('❌ Error exporting OTLP traces to OpenObserve:', error)
      
      // Fallback: Try legacy logs endpoint
      await this.flushLegacy(events)
    }
  }

  /**
   * Fallback: Send events in legacy format to logs endpoint
   */
  private async flushLegacy(events: SocketTraceEvent[]): Promise<void> {
    try {
      console.log('🔄 Falling back to legacy logs format...')
      
      // Convert to OpenObserve logs format
      const openObserveEvents = events.map(event => ({
        timestamp: event.timestamp * 1000000, // Convert to nanoseconds
        message: `Socket.IO Event: ${event.operationName}`,
        level: event.level.toUpperCase(),
        service: event.tags['service.name'] || 'aetherterm-frontend',
        trace_id: event.traceId,
        span_id: event.spanId,
        operation_name: event.operationName,
        duration_ms: event.duration || 0,
        status: event.status,
        ...event.tags
      }))

      // Send to OpenObserve logs endpoint
      const response = await fetch(`${this.config.endpoint}/v1/logs/${this.config.streamName}`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${btoa(`${this.config.username}:${this.config.password}`)}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(openObserveEvents)
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Failed to export to OpenObserve logs (fallback):', {
          status: response.status,
          statusText: response.statusText,
          error: errorText
        })
        
        // Re-add failed events to batch for retry
        this.batch.unshift(...events)
      } else {
        console.log(`✅ Exported ${events.length} events to OpenObserve Cloud (legacy logs)`)
      }

    } catch (error) {
      console.error('❌ Error exporting to OpenObserve (fallback):', error)
      
      // Re-add failed events to batch for retry
      this.batch.unshift(...events)
    }
  }

  /**
   * Start periodic flush
   */
  private startPeriodicFlush(): void {
    this.flushTimer = window.setInterval(() => {
      this.flush()
    }, this.flushInterval)
  }

  /**
   * Stop periodic flush and flush remaining events
   */
  public async shutdown(): Promise<void> {
    if (this.flushTimer) {
      clearInterval(this.flushTimer)
      this.flushTimer = null
    }

    // Flush remaining events
    await this.flush()
  }

  /**
   * Generate trace ID
   */
  private generateTraceId(): string {
    return Array.from({ length: 32 }, () => 
      Math.floor(Math.random() * 16).toString(16)
    ).join('')
  }

  /**
   * Generate span ID
   */
  private generateSpanId(): string {
    return Array.from({ length: 16 }, () => 
      Math.floor(Math.random() * 16).toString(16)
    ).join('')
  }

  /**
   * Get export statistics
   */
  public getStats(): { batchSize: number; pendingEvents: number } {
    return {
      batchSize: this.batchSize,
      pendingEvents: this.batch.length
    }
  }
}

// Global sink instance
let sinkInstance: OpenObserveSink | null = null

export const initializeOpenObserveSink = (): OpenObserveSink | null => {
  const endpoint = import.meta.env.VITE_OPENOBSERVE_ENDPOINT
  const username = import.meta.env.VITE_OPENOBSERVE_USER
  const password = import.meta.env.VITE_OPENOBSERVE_PASS
  const organization = import.meta.env.VITE_OPENOBSERVE_ORG

  if (!endpoint || !username || !password || !organization) {
    console.warn('⚠️ OpenObserve configuration incomplete - sink disabled')
    return null
  }

  sinkInstance = new OpenObserveSink({
    endpoint,
    organization,
    username,
    password,
    streamName: 'socket-io-traces'
  })

  return sinkInstance
}

export const getOpenObserveSink = (): OpenObserveSink | null => {
  return sinkInstance
}

export default OpenObserveSink