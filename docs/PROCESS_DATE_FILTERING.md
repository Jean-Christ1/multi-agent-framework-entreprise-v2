# Process Date Range Filtering

## Overview

This document describes the date range filtering functionality added to the `ProcessRepository.list_processes()` method, allowing users to filter processes by their creation timestamp.

## Feature Description

The `list_processes()` method now supports filtering processes based on their `created_at` timestamp using optional `from_date` and `to_date` parameters.

## API Reference

### Method Signature

```python
async def list_processes(
    self,
    *,
    status: Optional[ProcessStatus | str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[ProcessSchema]:
```

### Parameters

- `status` (Optional): Filter by process status (PENDING, RUNNING, COMPLETED, FAILED)
- `from_date` (Optional): Start of date range - returns processes created on or after this date
- `to_date` (Optional): End of date range - returns processes created on or before this date
- `limit` (int): Maximum number of results to return (default: 50)
- `offset` (int): Number of results to skip for pagination (default: 0)

### Return Value

Returns a list of `ProcessSchema` objects ordered by `updated_at` in descending order (most recently updated first).

## Usage Examples

### Filter by date range

```python
from datetime import datetime, timezone, timedelta

# Get processes created in the last 24 hours
now = datetime.now(timezone.utc)
yesterday = now - timedelta(days=1)

processes = await process_repo.list_processes(
    from_date=yesterday,
    to_date=now
)
```

### Filter by start date only

```python
# Get all processes created after a specific date
start_date = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

processes = await process_repo.list_processes(
    from_date=start_date
)
```

### Filter by end date only

```python
# Get all processes created before a specific date
end_date = datetime(2026, 1, 12, 23, 59, 59, tzinfo=timezone.utc)

processes = await process_repo.list_processes(
    to_date=end_date
)
```

### Combine with status filtering

```python
# Get completed processes from the last week
week_ago = datetime.now(timezone.utc) - timedelta(days=7)

processes = await process_repo.list_processes(
    status=ProcessStatus.COMPLETED,
    from_date=week_ago
)
```

## Implementation Details

### Database Query

The feature uses PostgreSQL's `TIMESTAMPTZ` column type for the `created_at` field, which stores timestamps with timezone information. The query filters using SQL comparison operators:

```sql
SELECT id, status, current_plan, context, created_at, updated_at
FROM processes
WHERE created_at >= :from_date AND created_at <= :to_date
ORDER BY updated_at DESC
LIMIT :limit OFFSET :offset
```

### Timezone Handling

- All timestamps are stored in UTC in the database
- The `created_at` field is automatically populated with `NOW()` on process creation
- Date parameters should be timezone-aware datetime objects (preferably UTC)
- Comparison with timezone-naive datetime objects may result in errors

## Testing

A comprehensive test suite validates the functionality:

- Filtering with both `from_date` and `to_date`
- Filtering with only `from_date`
- Filtering with only `to_date`
- Empty result sets when date range excludes all processes
- Correct ordering by `updated_at` DESC
- Timezone-aware datetime handling

Test file: `tests/persistence/test_process_repo.py::test_list_processes_filters_by_date_range`

## Database Schema

The `processes` table includes the following timestamp columns:

```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

Both columns use `TIMESTAMPTZ` (timestamp with timezone) to ensure proper timezone handling across different geographic locations.

## Best Practices

1. Always use timezone-aware datetime objects with UTC timezone
2. Use `datetime.now(timezone.utc)` for current timestamp
3. Combine date filtering with pagination (limit/offset) for large datasets
4. Consider adding indexes on `created_at` if filtering by creation date becomes a common query pattern
5. Use relative dates (e.g., "last 7 days") rather than hardcoded dates in production code

## Performance Considerations

- The existing index on `updated_at` supports the ORDER BY clause
- For optimal performance with date range queries on large datasets, consider adding an index:
  ```sql
  CREATE INDEX idx_processes_created_at ON processes(created_at DESC);
  ```
- Use pagination (limit/offset) to avoid loading large result sets into memory

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Overall system architecture
- [Database Migrations](../migrations/) - Database schema definitions
- [Process Repository](../framework/persistence/process_repo.py) - Full implementation
