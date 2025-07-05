/**
 * Frontend OpenTelemetry Configuration
 * 
 * Sets up browser-side tracing for AetherTerm frontend.
 */

import { trace } from '@opentelemetry/api'
import { WebTracerProvider } from '@opentelemetry/sdk-trace-web'
import { Resource } from '@opentelemetry/sdk-node'
import { getWebAutoInstrumentations } from '@opentelemetry/auto-instrumentations-web'
import { BatchSpanProcessor } from '@opentelemetry/sdk-trace-web'
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http'
import { registerInstrumentations } from '@opentelemetry/instrumentation'

interface TelemetryConfig {
  serviceName: string
  serviceVersion: string
  environment: string
  otlpEndpoint?: string
  apiKey?: string
  enableConsole?: boolean
  sampleRate?: number
}

class FrontendTelemetry {
  private provider: WebTracerProvider | null = null
  private config: TelemetryConfig
  
  constructor(config: Partial<TelemetryConfig> = {}) {
    this.config = {
      serviceName: 'aetherterm-frontend',
      serviceVersion: '0.0.1',
      environment: 'development',
      enableConsole: import.meta.env.DEV,
      sampleRate: 1.0,
      ...config
    }
  }
  
  initialize(): void {
    if (this.provider) {
      console.warn('Telemetry already initialized')
      return
    }
    
    try {
      // Create tracer provider
      this.provider = new WebTracerProvider({
        resource: new Resource({
          'service.name': this.config.serviceName,
          'service.version': this.config.serviceVersion,
          'deployment.environment': this.config.environment,
          'telemetry.sdk.language': 'javascript',
          'telemetry.sdk.name': 'opentelemetry',
        }),
      })
      
      // Configure exporters
      this.setupExporters()
      
      // Register the provider
      trace.setGlobalTracerProvider(this.provider)
      
      // Auto-instrument browser APIs
      this.setupInstrumentations()
      
      console.log('✅ Frontend telemetry initialized')
      
    } catch (error) {
      console.error('❌ Failed to initialize frontend telemetry:', error)
    }
  }
  
  private setupExporters(): void {
    if (!this.provider) return
    
    // OTLP exporter for Grafana Cloud
    if (this.config.otlpEndpoint && this.config.apiKey) {
      const otlpExporter = new OTLPTraceExporter({
        url: this.config.otlpEndpoint,
        headers: {
          'Authorization': `Basic ${this.config.apiKey}`
        },
      })
      
      this.provider.addSpanProcessor(
        new BatchSpanProcessor(otlpExporter)
      )
      
      console.log('📡 OTLP exporter configured for:', this.config.otlpEndpoint)
    }
    
    // Console exporter for development
    if (this.config.enableConsole) {
      const { ConsoleSpanExporter } = require('@opentelemetry/sdk-trace-web')
      const consoleExporter = new ConsoleSpanExporter()
      
      this.provider.addSpanProcessor(
        new BatchSpanProcessor(consoleExporter)
      )
      
      console.log('🖥️ Console exporter enabled for development')
    }
  }
  
  private setupInstrumentations(): void {
    // Auto-instrument common browser APIs
    registerInstrumentations({
      instrumentations: [
        getWebAutoInstrumentations({
          '@opentelemetry/instrumentation-fs': {
            enabled: false, // Not applicable for browser
          },
          '@opentelemetry/instrumentation-http': {
            enabled: false, // Use fetch instrumentation instead
          },
        }),
      ],
    })
  }
  
  getTracer(name: string = 'aetherterm-frontend') {
    return trace.getTracer(name, this.config.serviceVersion)
  }
  
  createSpan(name: string, attributes?: Record<string, string | number | boolean>) {
    const tracer = this.getTracer()
    return tracer.startSpan(name, { attributes })
  }
  
  // Convenience methods for common operations
  traceTerminalOperation(operation: string, sessionId: string) {
    return this.createSpan(`terminal.${operation}`, {
      'terminal.session.id': sessionId,
      'terminal.operation': operation,
    })
  }
  
  traceWebSocketEvent(event: string, messageType?: string) {
    return this.createSpan(`websocket.${event}`, {
      'websocket.event': event,
      'websocket.message.type': messageType || 'unknown',
    })
  }
  
  traceUserInteraction(action: string, component: string) {
    return this.createSpan(`user.${action}`, {
      'user.action': action,
      'ui.component': component,
    })
  }
  
  traceAPICall(method: string, endpoint: string) {
    return this.createSpan(`api.${method.toLowerCase()}`, {
      'http.method': method,
      'http.url': endpoint,
    })
  }
}

// Global instance
let telemetryInstance: FrontendTelemetry | null = null

export function initializeTelemetry(config?: Partial<TelemetryConfig>): FrontendTelemetry {
  if (!telemetryInstance) {
    telemetryInstance = new FrontendTelemetry(config)
    telemetryInstance.initialize()
  }
  return telemetryInstance
}

export function getTelemetry(): FrontendTelemetry | null {
  return telemetryInstance
}

// Environment-based configuration
export function getEnvironmentConfig(): Partial<TelemetryConfig> {
  return {
    serviceName: import.meta.env.VITE_OTEL_SERVICE_NAME || 'aetherterm-frontend',
    serviceVersion: import.meta.env.VITE_APP_VERSION || '0.0.1',
    environment: import.meta.env.VITE_ENVIRONMENT || 'development',
    otlpEndpoint: import.meta.env.VITE_GRAFANA_CLOUD_OTLP_ENDPOINT,
    apiKey: import.meta.env.VITE_GRAFANA_CLOUD_API_KEY,
    enableConsole: import.meta.env.DEV,
    sampleRate: parseFloat(import.meta.env.VITE_OTEL_TRACE_SAMPLE_RATE || '1.0'),
  }
}

// Auto-initialize if environment variables are present
if (typeof window !== 'undefined') {
  const config = getEnvironmentConfig()
  if (config.otlpEndpoint || config.enableConsole) {
    initializeTelemetry(config)
  }
}

export { FrontendTelemetry }