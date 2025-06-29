# Frontend Services

This directory contains service classes for API communication and business logic.

## InventoryApiService

The `InventoryApiService` handles all HTTP requests to the AetherTerm Inventory API.

### Features

- **REST API Integration**: Full CRUD operations for inventory resources
- **Search Functionality**: Real-time search across all inventory items
- **Provider Support**: Multi-cloud and on-premises provider support
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Legacy Compatibility**: Converts new API format to legacy format for UI compatibility

### Usage

```typescript
import { inventoryApiService } from './InventoryApiService'

// Get all resources
const resources = await inventoryApiService.getResources({ limit: 100 })

// Search inventory
const results = await inventoryApiService.searchInventory({
  search_term: 'web-server',
  provider_filter: 'aws'
})

// Get summary
const summary = await inventoryApiService.getInventorySummary()
```

### API Endpoints

- `GET /api/inventory/health` - Health check
- `GET /api/inventory/status` - Service status
- `GET /api/inventory/summary` - Inventory summary statistics
- `GET /api/inventory/resources` - Get all resources (with filtering)
- `POST /api/inventory/search` - Search inventory
- `POST /api/inventory/query` - Execute custom SQL query
- `GET /api/inventory/connections` - List connections
- `POST /api/inventory/connections` - Add connection
- `DELETE /api/inventory/connections/{name}` - Remove connection
- `GET /api/inventory/providers` - Get supported providers
- `POST /api/inventory/sync` - Trigger inventory sync

## AetherTermService (Extended)

The `AetherTermService` has been extended with inventory-related HTTP and WebSocket methods.

### New HTTP Methods

- `getInventorySummary()` - Get inventory summary
- `getInventoryResources()` - Get inventory resources with filtering
- `searchInventory()` - Search inventory
- `getInventoryServiceStatus()` - Get service status
- `syncInventory()` - Trigger inventory sync

### New WebSocket Events

- `inventory_update` - Real-time inventory updates
- `inventory_sync_status` - Sync progress updates
- `request_inventory_refresh` - Request inventory refresh
- `subscribe_resource_updates` - Subscribe to resource updates
- `unsubscribe_resource_updates` - Unsubscribe from resource updates

## Data Migration

The services handle migration from mock data to real API data seamlessly:

1. **Backward Compatibility**: Legacy UI components continue to work
2. **Format Conversion**: API data is converted to expected UI format
3. **Error Fallbacks**: Graceful degradation when API is unavailable
4. **Progressive Enhancement**: Features work with mock data but are enhanced with real data

## Configuration

The services use environment configuration from `config/environment.ts`:

```typescript
export const environment = {
  apiBaseUrl: 'http://localhost:57575', // Development
  // apiBaseUrl: '', // Production (uses current origin)
}
```

## Error Handling

All services implement comprehensive error handling:

- Network errors are caught and logged
- HTTP errors include detailed error messages
- UI components show user-friendly error states
- Retry mechanisms are provided for failed requests

## Performance

- **Caching**: Results are cached in Pinia stores
- **Lazy Loading**: Data is loaded on-demand
- **Pagination**: Large datasets use pagination
- **Debouncing**: Search requests are debounced to reduce API calls