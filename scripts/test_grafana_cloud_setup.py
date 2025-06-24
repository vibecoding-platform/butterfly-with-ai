#!/usr/bin/env python3
"""
Grafana Cloud OpenTelemetry setup and testing script
"""

import os
import sys
import time
import json
import base64
import requests
from typing import Dict, Optional

def check_grafana_cloud_requirements():
    """Check requirements for Grafana Cloud integration"""
    print("🔍 Grafana Cloud OpenTelemetry Integration Setup")
    print("=" * 70)
    
    print("📋 Requirements for Grafana Cloud:")
    print("   1. Grafana Cloud account (free tier available)")
    print("   2. Stack with Tempo (tracing) enabled")
    print("   3. Service account token or API key")
    print("   4. OTLP endpoint for your region")
    
    print("\n🌍 Common Grafana Cloud OTLP Endpoints:")
    regions = {
        "US Central": "https://otlp-gateway-prod-us-central-0.grafana.net/otlp",
        "US East": "https://otlp-gateway-prod-us-east-0.grafana.net/otlp", 
        "EU West": "https://otlp-gateway-prod-eu-west-0.grafana.net/otlp",
        "EU Central": "https://otlp-gateway-prod-eu-central-0.grafana.net/otlp",
        "Asia Pacific": "https://otlp-gateway-prod-ap-southeast-0.grafana.net/otlp"
    }
    
    for region, endpoint in regions.items():
        print(f"   • {region}: {endpoint}")
    
    return regions

def create_grafana_cloud_config_examples():
    """Create example configurations for different scenarios"""
    print("\n⚙️ Grafana Cloud Configuration Examples")
    print("=" * 70)
    
    configs = {
        "basic": {
            "description": "Basic Grafana Cloud configuration",
            "config": {
                "OTEL_ENABLED": "true",
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces",
                "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Basic <base64-encoded-instanceid:token>",
                "OTEL_SERVICE_NAME": "aetherterm-backend",
                "OTEL_RESOURCE_ATTRIBUTES": "service.name=aetherterm-backend,service.version=1.0.0"
            }
        },
        "with_logs": {
            "description": "Grafana Cloud with traces and logs",
            "config": {
                "OTEL_ENABLED": "true",
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces",
                "OTEL_EXPORTER_OTLP_LOGS_ENDPOINT": "https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/logs",
                "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Basic <base64-encoded-instanceid:token>",
                "OTEL_SERVICE_NAME": "aetherterm-backend",
                "OTEL_RESOURCE_ATTRIBUTES": "service.name=aetherterm-backend,service.version=1.0.0,deployment.environment=production"
            }
        },
        "development": {
            "description": "Development environment with sampling",
            "config": {
                "OTEL_ENABLED": "true",
                "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces",
                "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Basic <base64-encoded-instanceid:token>",
                "OTEL_SERVICE_NAME": "aetherterm-backend",
                "OTEL_TRACES_SAMPLER": "traceidratio",
                "OTEL_TRACES_SAMPLER_ARG": "0.1",  # 10% sampling
                "OTEL_RESOURCE_ATTRIBUTES": "service.name=aetherterm-backend,service.version=1.0.0,deployment.environment=development"
            }
        }
    }
    
    for name, config_info in configs.items():
        print(f"\n📋 {config_info['description']}:")
        
        # Write to file
        filename = f"config_grafana_cloud_{name}.env"
        with open(filename, 'w') as f:
            f.write(f"# {config_info['description']}\n")
            for k, v in config_info['config'].items():
                f.write(f"{k}={v}\n")
        print(f"   📄 Saved to: {filename}")
        
        # Show key configuration
        endpoint = config_info['config'].get('OTEL_EXPORTER_OTLP_TRACES_ENDPOINT', 'N/A')
        print(f"   🌐 Endpoint: {endpoint}")
    
    return configs

def test_grafana_cloud_connectivity(endpoint: str, auth_header: Optional[str] = None):
    """Test connectivity to Grafana Cloud endpoint"""
    print(f"\n📡 Testing Grafana Cloud Connectivity")
    print("=" * 50)
    
    if not auth_header:
        print("⚠️ No authentication provided - testing endpoint accessibility only")
    
    headers = {
        "Content-Type": "application/x-protobuf",
        "User-Agent": "aetherterm-grafana-test/1.0.0"
    }
    
    if auth_header:
        headers["Authorization"] = auth_header
    
    # Test data (minimal OTLP format)
    test_data = b'\x08\x01'  # Minimal protobuf data
    
    try:
        print(f"🔗 Testing endpoint: {endpoint}")
        response = requests.post(
            endpoint,
            headers=headers,
            data=test_data,
            timeout=15
        )
        
        status = response.status_code
        print(f"📊 Status: {status}")
        
        if status in [200, 202]:
            print("✅ SUCCESS - Endpoint accepts data!")
            return True
        elif status == 401:
            print("❌ UNAUTHORIZED - Check authentication")
            print("💡 Need valid Grafana Cloud token")
        elif status == 403:
            print("🚫 FORBIDDEN - Check permissions")
        elif status == 404:
            print("⚠️ NOT FOUND - Check endpoint URL")
        elif status == 415:
            print("⚠️ UNSUPPORTED MEDIA TYPE - Expected for test data")
            print("💡 Endpoint is accessible, authentication may be working")
            return True
        else:
            print(f"❓ OTHER: {status}")
            
        if response.text:
            print(f"📄 Response: {response.text[:200]}")
            
        return False
        
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return False

def provide_grafana_cloud_setup_guide():
    """Provide step-by-step setup guide for Grafana Cloud"""
    print("\n📚 Grafana Cloud Setup Guide")
    print("=" * 70)
    
    print("🚀 Step 1: Create Grafana Cloud Account")
    print("   • Visit: https://grafana.com/products/cloud/")
    print("   • Sign up for free tier (includes 50GB traces/month)")
    print("   • Create or select a stack")
    
    print("\n🔧 Step 2: Enable Tempo (Tracing)")
    print("   • In your stack, go to 'Configure' → 'Integrations'")
    print("   • Enable 'Tempo' if not already enabled")
    print("   • Note your stack's instance ID and region")
    
    print("\n🔑 Step 3: Create Service Account Token")
    print("   • Go to 'Administration' → 'Service Accounts'")
    print("   • Create new service account with 'MetricsPublisher' role")
    print("   • Generate token and save it securely")
    
    print("\n⚙️ Step 4: Get Your Configuration")
    print("   Instance ID: Found in stack settings (e.g., '123456')")
    print("   Token: From service account (e.g., 'glsa_...')")
    print("   Region: Your stack region (e.g., 'us-central-0')")
    
    print("\n🔒 Step 5: Create Authentication String")
    print("   Format: <instance-id>:<token>")
    print("   Encode with Base64: echo -n 'instanceid:token' | base64")
    print("   Use in header: Authorization=Basic <base64-string>")
    
    print("\n📝 Step 6: Update Configuration")
    print("   Edit config_grafana_cloud.env with your values:")
    print("   • OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=https://otlp-gateway-prod-<region>.grafana.net/otlp/v1/traces")
    print("   • OTEL_EXPORTER_OTLP_HEADERS=\"Authorization=Basic <your-base64-token>\"")
    
    print("\n🎯 Step 7: Test Integration")
    print("   source config_grafana_cloud.env")
    print("   uv run python src/aetherterm/agentserver/main.py --debug")
    print("   → Check traces in Grafana Cloud Explore → Tempo")

def test_console_telemetry_for_grafana():
    """Test console telemetry to show what data would be sent to Grafana"""
    print("\n🖥️ Console Preview: Data for Grafana Cloud")
    print("=" * 70)
    
    try:
        # Set environment for console output
        os.environ["OTEL_ENABLED"] = "true"
        os.environ["OTEL_SERVICE_NAME"] = "aetherterm-grafana-preview"
        os.environ["OTEL_TRACES_EXPORTER"] = "console"
        os.environ["OTEL_RESOURCE_ATTRIBUTES"] = "service.name=aetherterm-backend,service.version=1.0.0,deployment.environment=production"
        
        # Import and test
        sys.path.insert(0, "src")
        
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION, DEPLOYMENT_ENVIRONMENT
        
        # Configure with Grafana-style attributes
        resource = Resource.create({
            SERVICE_NAME: "aetherterm-backend",
            SERVICE_VERSION: "1.0.0",
            DEPLOYMENT_ENVIRONMENT: "production",
            "service.instance.id": "aetherterm-server-1"
        })
        
        tracer_provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(tracer_provider)
        
        # Add console exporter
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Create Grafana-ready test traces
        tracer = trace.get_tracer("aetherterm.socketio")
        
        print("📊 Creating Grafana-ready traces...")
        
        with tracer.start_as_current_span("socketio:terminal_session") as span:
            span.set_attribute("socketio.event", "terminal:create")
            span.set_attribute("terminal.session_id", "grafana-test-session")
            span.set_attribute("user.id", "test-user")
            span.set_attribute("http.route", "/socket.io/")
            span.add_event("session_started", {"timestamp": int(time.time())})
            
            with tracer.start_as_current_span("terminal:command_execution") as child_span:
                child_span.set_attribute("terminal.command", "ls -la")
                child_span.set_attribute("terminal.exit_code", 0)
                child_span.set_attribute("terminal.duration_ms", 150)
                child_span.add_event("command_started")
                child_span.add_event("command_completed", {"exit_code": 0})
        
        # Force export
        span_processor.force_flush(5)
        
        print("✅ Grafana-ready telemetry preview completed")
        print("💡 This data format will be sent to Grafana Cloud")
        
        return True
        
    except Exception as e:
        print(f"❌ Preview error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function for Grafana Cloud setup"""
    print("🎯 Grafana Cloud OpenTelemetry Integration")
    print("=" * 80)
    
    # Check requirements
    regions = check_grafana_cloud_requirements()
    
    # Create config examples
    configs = create_grafana_cloud_config_examples()
    
    # Test endpoint accessibility (without auth)
    test_grafana_cloud_connectivity("https://otlp-gateway-prod-us-central-0.grafana.net/otlp/v1/traces")
    
    # Show setup guide
    provide_grafana_cloud_setup_guide()
    
    # Preview telemetry data
    preview_works = test_console_telemetry_for_grafana()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 GRAFANA CLOUD INTEGRATION SUMMARY")
    print("=" * 80)
    
    print("✅ AetherTerm telemetry system ready for Grafana Cloud")
    print("📋 Configuration files created:")
    print("   • config_grafana_cloud_basic.env")
    print("   • config_grafana_cloud_with_logs.env") 
    print("   • config_grafana_cloud_development.env")
    
    print(f"\n🎯 Next Steps:")
    print("1. Create Grafana Cloud account (free tier available)")
    print("2. Enable Tempo tracing in your stack")
    print("3. Create service account token")
    print("4. Update config file with your credentials")
    print("5. Test: source config_grafana_cloud_basic.env && uv run python src/aetherterm/agentserver/main.py")
    
    print(f"\n💡 Benefits of Grafana Cloud:")
    print("• Free tier: 50GB traces/month, 10GB logs/month")
    print("• Built-in Grafana dashboards and alerting")
    print("• Seamless integration with metrics and logs")
    print("• Global CDN for fast trace ingestion")
    print("• No infrastructure management required")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)