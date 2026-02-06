# Code Style and Conventions

## Python Backend

### File Organization
- API routes in `api/` directory, one file per domain
- Core utilities in `core/` (config, database, security)
- Feature modules in `modules/` (ingest, extract, verify, etc.)
- Database models should be in `models/` (to be created)

### Naming Conventions
- Files: snake_case (e.g., `documents.py`, `auth_service.py`)
- Classes: PascalCase (e.g., `IngestModule`, `ProfileResponse`)
- Functions: snake_case (e.g., `create_profile`, `get_document`)
- Constants: UPPER_SNAKE_CASE (e.g., `ALGORITHM`, `QUERY_KEY`)

### Type Hints
- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable types
- Use `list[T]` and `dict[K, V]` (Python 3.9+ syntax)
- Use Pydantic models for request/response schemas

### Docstrings
- Triple-quoted docstrings for modules, classes, and public functions
- Include Args, Returns sections for complex functions
- Document security considerations in security-related code

### FastAPI Patterns
```python
# Router definition
router = APIRouter()

# Request/Response models with Pydantic
class ProfileCreate(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=255)

# Endpoint pattern
@router.post("/", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: ProfileCreate,
    db: AsyncSession = Depends(get_db)
):
    """Docstring explaining endpoint."""
    pass
```

### Error Handling
- Use HTTPException for API errors
- Include meaningful error messages
- Log errors appropriately

## TypeScript Frontend

### File Organization
- Components in `components/` with subdirectories for categories
- Pages in `pages/`
- API services in `services/`
- Hooks in `hooks/`

### Naming Conventions
- Files: PascalCase for components (e.g., `ProfileSetup.tsx`)
- Files: camelCase for services/hooks (e.g., `api.ts`, `useProfiles.ts`)
- Components: PascalCase
- Functions/Hooks: camelCase with `use` prefix for hooks

### TypeScript Patterns
```typescript
// Type definitions
interface Profile {
  id: string;
  display_name: string;
}

// React Query hooks
export function useProfiles() {
  return useQuery({
    queryKey: ['profiles'],
    queryFn: fetchProfiles,
  });
}
```

### Styling
- Tailwind CSS for styling
- Utility-first approach
- Custom classes in components when needed
