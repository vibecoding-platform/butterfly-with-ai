# AetherTerm Telemetry Alternatives (OpenObserve非使用)

OpenObserveに代わるtelemetry送信先の設定オプション

## 🎯 代替オプション

### 1. **Jaeger (分散トレーシング)**
```bash
# 環境変数設定
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:14268/api/traces
export OTEL_EXPORTER_OTLP_HEADERS=""  # 認証不要
```

### 2. **Grafana Cloud**
```bash
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces
export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic <base64-encoded-instance-id:api-key>"
```

### 3. **DataDog**
```bash
export OTEL_ENABLED=true
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://trace.agent.datadoghq.com/v1/traces
export DD_API_KEY=your-datadog-api-key
```

### 4. **Console Output (デバッグ用)**
```bash
export OTEL_ENABLED=true
export OTEL_TRACES_EXPORTER=console
export OTEL_LOGS_EXPORTER=console
```

### 5. **Prometheus + Grafana (メトリクス重視)**
```bash
export OTEL_ENABLED=true
export OTEL_METRICS_EXPORTER=prometheus
export OTEL_EXPORTER_PROMETHEUS_PORT=9090
```

## 🔧 設定の更新

以下のファイルを更新して、OpenObserve固有の実装を汎用化します：

### 1. 設定ファイル更新
```bash
# .env.example を汎用化
cp .env.example .env.example.backup
```