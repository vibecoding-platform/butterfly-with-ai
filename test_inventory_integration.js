#!/usr/bin/env node
/**
 * Simple integration test for inventory API
 * Run this to verify the inventory API endpoints are working
 */

const API_BASE = 'http://localhost:57575/api/inventory'

async function testEndpoint(endpoint, options = {}) {
  try {
    console.log(`Testing ${endpoint}...`)
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    const data = await response.json()
    console.log(`✅ ${endpoint} - OK`)
    return data
  } catch (error) {
    console.log(`❌ ${endpoint} - ${error.message}`)
    return null
  }
}

async function runTests() {
  console.log('🧪 Testing Inventory API Integration\n')
  
  // Test health check
  await testEndpoint('/health')
  
  // Test service status
  await testEndpoint('/status')
  
  // Test connections
  await testEndpoint('/connections')
  
  // Test supported providers
  await testEndpoint('/providers')
  
  // Test summary (might fail if no data)
  const summary = await testEndpoint('/summary')
  if (summary) {
    console.log(`   📊 Total resources: ${summary.total_resources}`)
  }
  
  // Test resources (might be empty)
  const resources = await testEndpoint('/resources?limit=5')
  if (resources) {
    console.log(`   📦 Found ${resources.length} resources`)
  }
  
  // Test search (might be empty)
  const searchResults = await testEndpoint('/search', {
    method: 'POST',
    body: JSON.stringify({
      search_term: 'server'
    })
  })
  if (searchResults) {
    console.log(`   🔍 Search found ${searchResults.length} results`)
  }
  
  console.log('\n✨ Integration test completed!')
  console.log('\nTo set up inventory data:')
  console.log('1. Start the AetherTerm server: make run-agentserver')
  console.log('2. Add connections via the API or web interface')
  console.log('3. Trigger a sync: POST /api/inventory/sync')
}

// Only run if called directly
if (require.main === module) {
  runTests().catch(console.error)
}

module.exports = { testEndpoint, runTests }