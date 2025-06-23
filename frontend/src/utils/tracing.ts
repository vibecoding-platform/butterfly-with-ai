/**
 * B3 Propagation Utilities for Frontend-Backend Trace Correlation
 * Compatible with OpenTelemetry B3 propagation format
 */

export interface B3TraceContext {
  traceId: string
  spanId: string
  sampled?: boolean
  parentSpanId?: string
}

/**
 * Generate a random hex string of specified length
 */
function generateHex(length: number): string {
  const bytes = new Uint8Array(length / 2)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
}

/**
 * Generate a new trace ID (32 hex characters)
 */
export function generateTraceId(): string {
  return generateHex(32)
}

/**
 * Generate a new span ID (16 hex characters)
 */
export function generateSpanId(): string {
  return generateHex(16)
}

/**
 * Create a new B3 trace context
 */
export function createB3TraceContext(parentSpanId?: string): B3TraceContext {
  return {
    traceId: generateTraceId(),
    spanId: generateSpanId(),
    sampled: true,
    parentSpanId
  }
}

/**
 * Convert B3 trace context to headers for HTTP/Socket.IO transmission
 */
export function b3ToHeaders(context: B3TraceContext): Record<string, string> {
  const headers: Record<string, string> = {}
  
  // B3 single header format
  let b3Value = `${context.traceId}-${context.spanId}`
  if (context.sampled !== undefined) {
    b3Value += `-${context.sampled ? '1' : '0'}`
  }
  if (context.parentSpanId) {
    b3Value += `-${context.parentSpanId}`
  }
  
  headers['b3'] = b3Value
  
  // Individual B3 headers (for compatibility)
  headers['x-b3-traceid'] = context.traceId
  headers['x-b3-spanid'] = context.spanId
  if (context.sampled !== undefined) {
    headers['x-b3-sampled'] = context.sampled ? '1' : '0'
  }
  if (context.parentSpanId) {
    headers['x-b3-parentspanid'] = context.parentSpanId
  }
  
  return headers
}

/**
 * Extract B3 trace context from headers
 */
export function b3FromHeaders(headers: Record<string, string>): B3TraceContext | null {
  // Try B3 single header first
  const b3Header = headers['b3'] || headers['B3']
  if (b3Header) {
    const parts = b3Header.split('-')
    if (parts.length >= 2) {
      const context: B3TraceContext = {
        traceId: parts[0],
        spanId: parts[1]
      }
      
      if (parts[2] !== undefined) {
        context.sampled = parts[2] === '1'
      }
      if (parts[3]) {
        context.parentSpanId = parts[3]
      }
      
      return context
    }
  }
  
  // Try individual headers
  const traceId = headers['x-b3-traceid'] || headers['X-B3-TraceId']
  const spanId = headers['x-b3-spanid'] || headers['X-B3-SpanId']
  
  if (traceId && spanId) {
    const context: B3TraceContext = { traceId, spanId }
    
    const sampled = headers['x-b3-sampled'] || headers['X-B3-Sampled']
    if (sampled !== undefined) {
      context.sampled = sampled === '1'
    }
    
    const parentSpanId = headers['x-b3-parentspanid'] || headers['X-B3-ParentSpanId']
    if (parentSpanId) {
      context.parentSpanId = parentSpanId
    }
    
    return context
  }
  
  return null
}

/**
 * Add B3 trace context to Socket.IO data
 */
export function addTraceContextToSocketData(data: any, context?: B3TraceContext): any {
  const traceContext = context || createB3TraceContext()
  
  if (data && typeof data === 'object') {
    return {
      ...data,
      _trace: {
        traceId: traceContext.traceId,
        spanId: traceContext.spanId,
        sampled: traceContext.sampled,
        parentSpanId: traceContext.parentSpanId
      }
    }
  } else {
    return {
      _originalData: data,
      _trace: {
        traceId: traceContext.traceId,
        spanId: traceContext.spanId,
        sampled: traceContext.sampled,
        parentSpanId: traceContext.parentSpanId
      }
    }
  }
}

/**
 * Extract B3 trace context from Socket.IO data
 */
export function extractTraceContextFromSocketData(data: any): B3TraceContext | null {
  if (data && typeof data === 'object' && data._trace) {
    return {
      traceId: data._trace.traceId,
      spanId: data._trace.spanId,
      sampled: data._trace.sampled,
      parentSpanId: data._trace.parentSpanId
    }
  }
  
  return null
}

/**
 * Create a child span context from parent
 */
export function createChildSpanContext(parent: B3TraceContext): B3TraceContext {
  return {
    traceId: parent.traceId, // Same trace ID
    spanId: generateSpanId(), // New span ID
    sampled: parent.sampled,
    parentSpanId: parent.spanId // Current span becomes parent
  }
}

/**
 * Format trace context for logging
 */
export function formatTraceContext(context: B3TraceContext): string {
  let formatted = `trace=${context.traceId.substring(0, 8)}...${context.traceId.substring(-4)} span=${context.spanId.substring(0, 8)}...${context.spanId.substring(-4)}`
  
  if (context.parentSpanId) {
    formatted += ` parent=${context.parentSpanId.substring(0, 8)}...${context.parentSpanId.substring(-4)}`
  }
  
  if (context.sampled !== undefined) {
    formatted += ` sampled=${context.sampled}`
  }
  
  return formatted
}