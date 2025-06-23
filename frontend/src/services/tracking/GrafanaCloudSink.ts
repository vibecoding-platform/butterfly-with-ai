/**
 * Grafana Cloud Sink
 * Socket.IO tracking data sink to Grafana Cloud Tempo
 */

export interface GrafanaCloudConfig {
  otlpEndpoint: string
  authToken: string  // Base64 encoded authorization header
  serviceName: string
  serviceNamespace: string
  environment: string
  protocol: 'http/protobuf' | 'http/json'
  debug: boolean
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

// OTLP-compliant trace data structure for Grafana Cloud Tempo
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
    scopeSpans: Array<{
      scope: {
        name: string
        version: string
      }
      spans: OTLPSpan[]
    }>
  }>
}

export class GrafanaCloudSink {
  private config: GrafanaCloudConfig
  private batchSize = 10
  private flushInterval = 5000 // 5 seconds
  private batch: SocketTraceEvent[] = []
  private flushTimer: number | null = null

  constructor(config: GrafanaCloudConfig) {
    this.config = config

    console.log('📊 Grafana Cloud Sink initialized', {
      endpoint: this.config.otlpEndpoint,
      serviceName: this.config.serviceName,
      environment: this.config.environment,
      protocol: this.config.protocol
    })

    // Start periodic flush
    this.startPeriodicFlush()
  }

  /**
   * Export socket trace event to Grafana Cloud
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
        'service.name': this.config.serviceName,
        'service.version': '1.0.0',
        'deployment.environment': this.config.environment,
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
        'service.name': this.config.serviceName,
        'socket.url': window.location.origin,
        'deployment.environment': this.config.environment,
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
        'service.name': this.config.serviceName,
        'deployment.environment': this.config.environment,
        ...metadata
      },
      status: 'timeout',
      level: 'warn'
    }

    this.exportTrace(traceEvent)
  }

  /**
   * Convert SocketTraceEvent to OTLP format for Grafana Cloud Tempo
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
              value: { stringValue: this.config.serviceName }
            },
            {
              key: 'service.namespace',
              value: { stringValue: this.config.serviceNamespace }
            },
            {
              key: 'service.version',
              value: { stringValue: '1.0.0' }
            },
            {
              key: 'deployment.environment',
              value: { stringValue: this.config.environment }
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
        scopeSpans: [{
          scope: {
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
   * Flush current batch to Grafana Cloud using OTLP format
   */
  public async flush(): Promise<void> {
    if (this.batch.length === 0) return

    const events = [...this.batch]
    this.batch = []

    try {
      // Convert to OTLP format
      const otlpData = this.convertToOTLP(events)

      // Determine content type based on protocol
      const contentType = this.config.protocol === 'http/protobuf' 
        ? 'application/x-protobuf'
        : 'application/json'

      // Send to Grafana Cloud Tempo OTLP endpoint
      const response = await fetch(`${this.config.otlpEndpoint}/v1/traces`, {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${this.config.authToken}`,
          'Content-Type': contentType,
          'User-Agent': 'aetherterm-socket-tracing/1.0.0'
        },
        body: this.config.protocol === 'http/protobuf' 
          ? this.encodeProtobuf(otlpData)  // TODO: Implement protobuf encoding
          : JSON.stringify(otlpData)
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ Failed to export OTLP traces to Grafana Cloud:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText
        })
        
        // Re-add failed events to batch for retry
        this.batch.unshift(...events)
      } else {
        if (this.config.debug) {
          console.log(`✅ Exported ${events.length} OTLP traces to Grafana Cloud Tempo`)
        }
      }

    } catch (error) {
      console.error('❌ Error exporting OTLP traces to Grafana Cloud:', error)
      
      // Re-add failed events to batch for retry
      this.batch.unshift(...events)
    }
  }

  /**
   * Encode OTLP data as protobuf (placeholder implementation)
   * In production, you would use a proper protobuf library
   */
  private encodeProtobuf(data: OTLPTraceData): ArrayBuffer {
    // For now, fallback to JSON encoding
    // TODO: Implement proper protobuf encoding using @opentelemetry/otlp-transformer
    console.warn('⚠️ Protobuf encoding not implemented, falling back to JSON')
    return new TextEncoder().encode(JSON.stringify(data))
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
   * Generate trace ID (32 hex characters)
   */
  private generateTraceId(): string {
    return Array.from({ length: 32 }, () => 
      Math.floor(Math.random() * 16).toString(16)
    ).join('')
  }

  /**
   * Generate span ID (16 hex characters)
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
let sinkInstance: GrafanaCloudSink | null = null

export const initializeGrafanaCloudSink = (): GrafanaCloudSink | null => {
  const otlpEndpoint = import.meta.env.VITE_GRAFANA_OTLP_ENDPOINT
  const authToken = import.meta.env.VITE_GRAFANA_AUTH_TOKEN
  const serviceName = import.meta.env.VITE_SERVICE_NAME || 'aetherterm'
  const serviceNamespace = import.meta.env.VITE_SERVICE_NAMESPACE || 'aetherterm-frontend'
  const environment = import.meta.env.VITE_ENVIRONMENT || 'development'
  const protocol = import.meta.env.VITE_GRAFANA_PROTOCOL || 'http/json'
  const debug = import.meta.env.VITE_DEBUG_TELEMETRY === 'true'

  if (!otlpEndpoint || !authToken) {
    console.warn('⚠️ Grafana Cloud configuration incomplete - sink disabled')
    return null
  }

  sinkInstance = new GrafanaCloudSink({
    otlpEndpoint,
    authToken,
    serviceName,
    serviceNamespace,
    environment,
    protocol: protocol as 'http/protobuf' | 'http/json',
    debug
  })

  return sinkInstance
}

export const getGrafanaCloudSink = (): GrafanaCloudSink | null => {
  return sinkInstance
}

export default GrafanaCloudSink