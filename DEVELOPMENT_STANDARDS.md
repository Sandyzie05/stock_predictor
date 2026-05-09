# Development Standards & Cursor Rules

## Core Principles
1. **Test-Driven Development**: Write tests alongside implementation, never after
2. **Async-First**: All I/O operations use async/await patterns
3. **Type Safety**: Comprehensive typing with dataclasses and type hints
4. **Resource Management**: Always use context managers for external resources
5. **Graceful Degradation**: Handle errors without crashing, return None/empty on failure

## Established Patterns

### 1. Service Architecture Pattern
```python
# Standard service structure
class ServiceName:
    def __init__(self):
        self.config = settings.RELEVANT_CONFIG
        self.resource: Optional[Resource] = None
    
    async def __aenter__(self):
        self.resource = await create_resource()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.resource:
            await self.resource.close()
    
    async def main_method(self, param: Type) -> Optional[ReturnType]:
        if not self.resource:
            raise RuntimeError("Service must be used as async context manager")
        
        try:
            # Implementation
            return result
        except Exception as e:
            print(f"Error in {self.__class__.__name__}: {e}")
            return None
```

### 2. Data Class Pattern
```python
@dataclass
class DataClassName:
    """Clear docstring describing the data."""
    required_field: Type
    optional_field: Optional[Type] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
```

### 3. Test Structure Pattern
```python
class TestServiceName:
    """Test ServiceName."""
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager functionality."""
        async with ServiceName() as service:
            assert service.resource is not None
        assert service.resource.closed
    
    @pytest.mark.asyncio
    async def test_main_method_success(self):
        """Test successful operation."""
        with patch('module.dependency') as mock_dep:
            mock_dep.return_value = expected_result
            
            async with ServiceName() as service:
                result = await service.main_method(test_input)
                
                assert result is not None
                assert result.field == expected_value
```

### 4. File Organization Pattern
```
app/services/
├── __init__.py          # Import only implemented services
├── service_name.py      # Main implementation
└── ...

tests/test_services/
├── __init__.py
├── test_service_name.py # Comprehensive tests
└── ...
```

## Development Workflow

### 1. Before Implementation
- [ ] Define clear data classes for inputs/outputs
- [ ] Plan async context manager structure
- [ ] Identify external dependencies and error scenarios

### 2. Implementation Order
1. Create data classes
2. Create service class with context manager
3. Implement core methods with error handling
4. Create comprehensive test suite
5. Run tests and verify 100% pass rate
6. Update version history
7. Update TODO progress

### 3. Testing Standards
- **Minimum 90%+ pass rate** before proceeding
- **Mock all external dependencies** (APIs, databases, files)
- **Test error scenarios** (network failures, invalid data, missing resources)
- **Test async patterns** properly with pytest.mark.asyncio
- **Test resource cleanup** (context managers, session closing)

### 4. Error Handling Standards
```python
try:
    result = await external_operation()
    return process_result(result)
except SpecificException as e:
    print(f"Specific error in {method_name}: {e}")
    return None
except Exception as e:
    print(f"Unexpected error in {method_name}: {e}")
    return None
```

### 5. Import Management
- Only import implemented services in `__init__.py`
- Use TODO comments for future imports
- Add imports only after implementation is complete

## Code Quality Rules

### 1. Efficiency Rules
- **No redundant implementations** - reuse established patterns
- **Consistent naming conventions** - follow existing patterns
- **DRY principle** - extract common functionality
- **Single responsibility** - each service has one clear purpose

### 2. Documentation Rules
- **Docstrings for all classes and methods**
- **Type hints for all function signatures**  
- **Clear variable names** with context
- **Update VERSION_HISTORY.md** for all changes

### 3. Performance Rules
- **Async/await for all I/O operations**
- **Connection pooling** where applicable
- **Graceful resource cleanup**
- **Minimal blocking operations**

## Service Dependencies

### Current Architecture
```
DataFetcherService (✅ Implemented)
├── External APIs (Polygon, NewsAPI, Yahoo Finance)
├── HTTP session management
└── Data normalization

StockAnalyzerService (Next)
├── Depends on: DataFetcherService
├── Technical indicators calculation
└── Fundamental analysis

PredictionEngineService (Future)
├── Depends on: DataFetcherService, StockAnalyzerService
├── ML model training/inference
└── Prediction generation

RecommendationEngineService (Future)
├── Depends on: All above services
├── Business logic for recommendations
└── Risk assessment
```

## Version Control Standards
- **Semantic versioning**: Major.Minor.Patch
- **Detailed change logs** with rationale
- **Impact assessment** for each change
- **Next steps documentation**

## Anti-Patterns to Avoid
- ❌ Implementing without tests
- ❌ Blocking I/O operations  
- ❌ Missing error handling
- ❌ Hardcoded configuration
- ❌ Resource leaks (unclosed sessions)
- ❌ Redundant code patterns
- ❌ Missing type hints

## Success Metrics
- ✅ 100% test pass rate
- ✅ Full async implementation
- ✅ Comprehensive error handling
- ✅ Type safety throughout
- ✅ Resource cleanup verified
- ✅ Documentation complete
