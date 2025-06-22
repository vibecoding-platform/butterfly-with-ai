/**
 * OpenTelemetryService for AetherTerm
 * Comprehensive observability with Traces and Metrics for OpenObserve
 * Compatible with OpenTelemetry v0.26.x
 */

import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import { Resource } from '@opentelemetry/resources'
import { SemanticResourceAttributes } from '@opentelemetry/semantic-conventions'
import { SimpleSpanProcessor, ConsoleSpanExporter } from '@opentelemetry/sdk-trace-base'
import { 
  trace, 
  SpanKind, 
  SpanStatusCode
} from '@opentelemetry/api'
import type { Span, Tracer } from '@opentelemetry/api'

export interface OpenTelemetryConfig {
  endpoint: string
  organization: string
  stream: string
  username: string
  password: string
  serviceName: string
  serviceNamespace: string
  environment: string
  debug: boolean
}

export interface ErrorBoundaryInfo {
  componentName: string
  propsData?: Record<string, any>
  error: Error
  errorInfo?: any
  componentStack?: string
  errorBoundary: string
}

export interface TerminalOperationContext {
  terminalId: string
  operation: string
  sessionId?: string
  userId?: string
}

export interface UserContext {
  userId?: string
  sessionId?: string
  componentName?: string
  workspaceId?: string
  tabId?: string
  paneId?: string
}

class OpenTelemetryService {
  private tracer: Tracer | null = null
  private provider: WebTracerProvider | null = null
  private config: OpenTelemetryConfig | null = null
  private userContext: UserContext = {}
  private isInitialized = false

  private getDefaultConfig(): OpenTelemetryConfig {
    return {
      endpoint: import.meta.env.VUE_APP_OPENOBSERVE_ENDPOINT || 'https://api.openobserve.ai/api/2xzmUQoXwbYU1DOjfVOknSPGOgP',
      organization: import.meta.env.VUE_APP_OPENOBSERVE_ORG || 'default',
      stream: import.meta.env.VUE_APP_OPENOBSERVE_STREAM || 'default',
      username: import.meta.env.VUE_APP_OPENOBSERVE_USERNAME || 'kaz@re-x.info',
      password: import.meta.env.VUE_APP_OPENOBSERVE_PASSWORD || 'c8KGNeJfJIbZqFu7',
      serviceName: import.meta.env.VUE_APP_SERVICE_NAME || 'aetherterm-frontend',
      serviceNamespace: import.meta.env.VUE_APP_SERVICE_NAMESPACE || 'aetherterm',
      environment: import.meta.env.NODE_ENV || 'development',
      debug: import.meta.env.VUE_APP_DEBUG_TELEMETRY === 'true'
    }
  }

  async initialize(config?: Partial<OpenTelemetryConfig>): Promise<void> {
    if (this.isInitialized) {
      console.warn('OpenTelemetry service already initialized')
      return
    }

    try {
      this.config = { ...this.getDefaultConfig(), ...config }

      if (this.config.debug) {
        console.log('🔧 Initializing OpenTelemetry with config:', {
          ...this.config,
          password: '***'
        })
      }

      // Create resource
      const resource = new Resource({
        [SemanticResourceAttributes.SERVICE_NAME]: this.config.serviceName,
        [SemanticResourceAttributes.SERVICE_NAMESPACE]: this.config.serviceNamespace,
        [SemanticResourceAttributes.SERVICE_VERSION]: import.meta.env.VUE_APP_VERSION || '1.0.0',
        [SemanticResourceAttributes.DEPLOYMENT_ENVIRONMENT]: this.config.environment,
      })

      // Create tracer provider
      this.provider = new WebTracerProvider({
        resource
      })

      // Create console span exporter for development feedback
      const consoleExporter = new ConsoleSpanExporter()

      // Create custom HTTP sink for OpenObserve Cloud
      const openObserveSink = this.createOpenObserveSink()

      // Add span processors
      if (this.config.debug || this.config.environment === 'development') {
        // Console exporter for immediate development feedback
        this.provider.addSpanProcessor(new SimpleSpanProcessor(consoleExporter))
      }
      
      if (openObserveSink) {
        // OpenObserve sink for cloud telemetry
        this.provider.addSpanProcessor(new SimpleSpanProcessor(openObserveSink))
      }

      // Register the provider
      this.provider.register()

      // Get tracer
      this.tracer = trace.getTracer(this.config.serviceName)

      // Auto-instrumentations can be added here later when compatibility is resolved
      // registerInstrumentations({ instrumentations: [...] })

      this.isInitialized = true

      if (this.config.debug) {
        console.log('✅ OpenTelemetry initialized successfully')
      }

    } catch (error) {
      console.error('❌ Failed to initialize OpenTelemetry:', error)
      throw error
    }
  }

  updateContext(context: Partial<UserContext>): void {
    this.userContext = { ...this.userContext, ...context }
  }

  createSpan(name: string, attributes?: Record<string, any>): Span | null {
    if (!this.tracer) {
      console.warn('OpenTelemetry tracer not initialized')
      return null
    }

    const span = this.tracer.startSpan(name, {
      kind: SpanKind.CLIENT,
      attributes: {
        ...attributes,
        ...this.getUserContextAttributes()
      }
    })

    return span
  }

  traceUserInteraction(action: string, target?: string, metadata?: Record<string, any>): Span | null {
    return this.createSpan('user_interaction', {
      'user.action': action,
      'user.target': target,
      'interaction.type': 'click',
      ...metadata
    })
  }

  traceTerminalOperation(context: TerminalOperationContext): Span | null {
    return this.createSpan(`terminal.${context.operation}`, {
      'terminal.id': context.terminalId,
      'terminal.operation': context.operation,
      'terminal.session_id': context.sessionId,
      'terminal.user_id': context.userId
    })
  }

  traceSocketOperation(event: string, data?: any): Span | null {
    return this.createSpan(`socket.${event}`, {
      'socket.event': event,
      'socket.data_size': data ? JSON.stringify(data).length : 0,
      'socket.has_data': !!data
    })
  }

  traceWorkspaceOperation(operation: string, workspaceId: string, metadata?: Record<string, any>): Span | null {
    return this.createSpan(`workspace.${operation}`, {
      'workspace.id': workspaceId,
      'workspace.operation': operation,
      ...metadata
    })
  }

  // Simplified logging without OpenTelemetry Logs API
  logInfo(message: string, attributes?: Record<string, any>): void {
    const logData = {
      timestamp: new Date().toISOString(),
      level: 'info',
      message,
      service: this.config?.serviceName,
      ...this.userContext,
      ...attributes
    }

    if (this.config?.debug) {
      console.log('📊 OpenTelemetry Log [INFO]:', logData)
    }

    // Send to OpenObserve via console for now
    // In production, you'd send this via HTTP to OpenObserve logs endpoint
    this.sendLogToConsole('INFO', message, logData)
  }

  logError(message: string, error: Error, attributes?: Record<string, any>): void {
    const logData = {
      timestamp: new Date().toISOString(),
      level: 'error',
      message,
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack
      },
      service: this.config?.serviceName,
      ...this.userContext,
      ...attributes
    }

    if (this.config?.debug) {
      console.error('📊 OpenTelemetry Log [ERROR]:', logData)
    }

    this.sendLogToConsole('ERROR', message, logData)
  }

  logWarning(message: string, attributes?: Record<string, any>): void {
    const logData = {
      timestamp: new Date().toISOString(),
      level: 'warning',
      message,
      service: this.config?.serviceName,
      ...this.userContext,
      ...attributes
    }

    if (this.config?.debug) {
      console.warn('📊 OpenTelemetry Log [WARNING]:', logData)
    }

    this.sendLogToConsole('WARN', message, logData)
  }

  logErrorBoundary(boundaryInfo: ErrorBoundaryInfo): void {
    const span = this.createSpan('error_boundary_triggered', {
      'error.boundary': boundaryInfo.errorBoundary,
      'error.component': boundaryInfo.componentName,
      'error.name': boundaryInfo.error.name,
      'error.message': boundaryInfo.error.message,
      'error.has_stack': !!boundaryInfo.error.stack,
      'error.has_component_stack': !!boundaryInfo.componentStack
    })

    if (span) {
      span.recordException(boundaryInfo.error)
      span.setStatus({
        code: SpanStatusCode.ERROR,
        message: boundaryInfo.error.message
      })
      span.end()
    }

    this.logError('Vue Error Boundary triggered', boundaryInfo.error, {
      component_name: boundaryInfo.componentName,
      error_boundary: boundaryInfo.errorBoundary,
      props_data: boundaryInfo.propsData,
      component_stack: boundaryInfo.componentStack
    })
  }

  private getUserContextAttributes(): Record<string, any> {
    return Object.keys(this.userContext).reduce((acc, key) => {
      acc[`user.${key}`] = this.userContext[key as keyof UserContext]
      return acc
    }, {} as Record<string, any>)
  }

  private sendLogToConsole(level: string, message: string, data: any): void {
    // In a real implementation, this would send to OpenObserve logs endpoint
    const logEntry = `[${level}] ${message} | ${JSON.stringify(data)}`
    
    switch (level) {
      case 'ERROR':
        console.error(logEntry)
        break
      case 'WARN':
        console.warn(logEntry)
        break
      default:
        console.log(logEntry)
    }
  }

  // Create custom OpenObserve HTTP sink
  private createOpenObserveSink(): any {
    if (!this.config) return null

    try {
      // Custom HTTP sink for OpenObserve Cloud
      return {
        export: (spans: any[], resultCallback: (result: any) => void) => {
          this.exportSpansToOpenObserve(spans).then(() => {
            resultCallback({ code: 0 }) // SUCCESS
          }).catch((error) => {
            console.error('Failed to export spans to OpenObserve:', error)
            resultCallback({ code: 1, error }) // FAILED
          })
        },
        shutdown: async () => {
          // Cleanup if needed
        }
      }
    } catch (error) {
      console.error('Failed to create OpenObserve sink:', error)
      return null
    }
  }

  // Export spans to OpenObserve via HTTP
  private async exportSpansToOpenObserve(spans: any[]): Promise<void> {
    if (!this.config || spans.length === 0) return

    try {
      const traceData = {
        resourceSpans: [{
          resource: {
            attributes: [{
              key: 'service.name',
              value: { stringValue: this.config.serviceName }
            }, {
              key: 'service.namespace',
              value: { stringValue: this.config.serviceNamespace }
            }]
          },
          instrumentationLibrarySpans: [{
            instrumentationLibrary: {
              name: this.config.serviceName,
              version: '1.0.0'
            },
            spans: spans.map(span => ({
              traceId: span.spanContext?.traceId || '',
              spanId: span.spanContext?.spanId || '',
              parentSpanId: span.parentSpanId || '',
              name: span.name || 'unknown',
              kind: span.kind || 1,
              startTimeUnixNano: span.startTime ? String(span.startTime[0] * 1000000 + span.startTime[1]) : '0',
              endTimeUnixNano: span.endTime ? String(span.endTime[0] * 1000000 + span.endTime[1]) : '0',
              attributes: Object.entries(span.attributes || {}).map(([key, value]) => ({
                key,
                value: { stringValue: String(value) }
              })),
              status: {
                code: span.status?.code || 0,
                message: span.status?.message || ''
              }
            }))
          }]
        }]
      }

      const response = await fetch(`${this.config.endpoint}/v1/traces`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Basic ${btoa(`${this.config.username}:${this.config.password}`)}`
        },
        body: JSON.stringify(traceData)
      })

      if (!response.ok) {
        throw new Error(`OpenObserve export failed: ${response.status} ${response.statusText}`)
      }

      if (this.config.debug) {
        console.log(`📤 Exported ${spans.length} spans to OpenObserve Cloud`)
      }

    } catch (error) {
      console.error('Failed to export spans to OpenObserve:', error)
      throw error
    }
  }

  // Shutdown method
  async shutdown(): Promise<void> {
    if (this.provider) {
      await this.provider.shutdown()
      this.isInitialized = false
      
      if (this.config?.debug) {
        console.log('🔌 OpenTelemetry service shut down')
      }
    }
  }
}

// Export singleton instance
export const openTelemetryService = new OpenTelemetryService()
export { OpenTelemetryService }