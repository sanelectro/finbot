# Testing Suite

**Comprehensive integration and validation testing for FinBot architecture**

The testing suite validates the complete FinBot pipeline from document ingestion through search functionality, with emphasis on RBAC enforcement and natural language query accuracy.

## 🧪 Test Architecture

### Testing Philosophy
- **Integration-first**: Test complete workflows, not isolated components
- **Natural language focus**: Use realistic user queries, not keyword matching
- **RBAC validation**: Verify security enforcement at every level
- **Performance monitoring**: Track response times and accuracy metrics

### Test Structure
```
src/tests/
├── test_ingestion_and_search.py    # Main integration test suite
├── fixtures/                       # Test data and configurations
├── results/                        # Test output and reports
└── docs/                          # This documentation
```

## 📋 Core Test Suite

### 🔄 Integration Test (`test_ingestion_and_search.py`)

**Complete end-to-end workflow validation**

#### Test Workflow
```python
class FinBotTester:
    async def run_comprehensive_test():
        # 1. Clear and setup collection
        await self.clear_and_setup_collection()
        
        # 2. Ingest engineering document 
        doc = await self.ingest_engineering_document()
        
        # 3. Test search functionality
        await self.test_search_functionality()
        
        # 4. Test RBAC filtering
        await self.test_rbac_filtering()
        
        # 5. Show collection statistics
        await self.show_collection_stats()
```

#### Document Processing Tests
```python
async def test_document_processing(self):
    """Validate document chunking and metadata generation"""
    processor = HierarchicalDocumentProcessor()
    doc = await processor.process_document(
        Path('data/engineering/system_sla_report_2024.md'),
        'engineering'
    )
    
    # Validate processing results
    assert len(doc.chunks) > 0, "Document should produce chunks"
    assert doc.processing_time > 0, "Processing time should be recorded"
    assert doc.file_size > 0, "File size should be captured"
    
    # Validate chunk structure 
    for chunk in doc.chunks:
        assert isinstance(chunk.headings, list), "Headings must be list"
        assert chunk.content.strip(), "Content must not be empty"
        assert chunk.chunk_text, "Chunk text must be generated"
        assert chunk.metadata.collection == 'engineering', "Collection must match"
        assert 'engineering' in chunk.metadata.access_roles, "RBAC roles must be set"
```

#### Vector Storage Tests
```python
async def test_vector_storage(self):
    """Validate vector database storage and retrieval"""
    vector_store = VectorStore()
    
    # Test collection initialization
    success = await vector_store.initialize_collection(recreate=True)
    assert success, "Collection initialization must succeed"
    
    # Test document storage
    success = await vector_store.store_documents([doc])
    assert success, "Document storage must succeed"
    
    # Validate embeddings
    for chunk in doc.chunks:
        assert chunk.embedding is not None, "Embeddings must be generated"
        assert len(chunk.embedding) == 384, "Embedding dimension must be 384"
        assert all(isinstance(x, float) for x in chunk.embedding), "Embeddings must be floats"
```

## 🔍 Search Validation Tests

### Natural Language Query Testing
```python
SEARCH_TEST_QUERIES = [
    ("What are the overall sprint performance metrics?", "sprint/performance content"),
    ("What is our system uptime and SLA compliance?", "SLA and uptime information"),  
    ("Give me a summary of our system performance", "executive summary sections"),
    ("What are the access restrictions for engineering documents?", "engineering team content"),
    ("How do we measure our system performance indicators?", "KPI and metrics"),
    ("Tell me about FinSolve Technologies system reports", "company-related content"),
]

async def test_search_functionality(self):
    """Test semantic search with natural language queries"""
    for query, expected_content in SEARCH_TEST_QUERIES:
        results = await self.vector_store.search_with_rbac(
            query=query,
            user_role='engineering',
            limit=3,
            score_threshold=0.2
        )
        
        # Validate results structure
        assert len(results) > 0, f"Query '{query}' should return results"
        
        for chunk, score in results:
            # Validate score range
            assert 0.0 <= score <= 1.0, f"Score {score} must be in [0,1] range"
            
            # Validate breadcrumb integration
            if chunk.headings:
                breadcrumb = " > ".join(chunk.headings)
                assert breadcrumb in chunk.chunk_text, "Breadcrumb must be in chunk_text"
            
            # Validate metadata
            assert chunk.metadata.collection in ['engineering'], "Collection must be accessible"
            assert 'engineering' in chunk.metadata.access_roles, "RBAC must allow access"
```

### Search Accuracy Metrics
```python
async def measure_search_accuracy(self):
    """Measure and report search accuracy metrics"""
    accuracy_results = []
    
    for query, expected_content in SEARCH_TEST_QUERIES:
        results = await self.vector_store.search_with_rbac(query, 'engineering', limit=5)
        
        if results:
            top_score = results[0][1]  # Best match score
            avg_score = sum(score for _, score in results) / len(results)
            
            accuracy_results.append({
                'query': query,
                'top_score': top_score, 
                'avg_score': avg_score,
                'result_count': len(results)
            })
    
    # Generate accuracy report
    overall_accuracy = sum(r['top_score'] for r in accuracy_results) / len(accuracy_results)
    print(f"📊 Overall search accuracy: {overall_accuracy:.3f}")
    
    return accuracy_results
```

## 🔐 RBAC Security Tests

### Role-Based Access Validation
```python
async def test_rbac_enforcement(self):
    """Comprehensive RBAC security testing"""
    test_cases = [
        # (user_role, expected_results, description)
        ('engineering', True, "Engineering should access engineering documents"),
        ('finance', False, "Finance should NOT access engineering documents"),
        ('c_level', True, "C-level should access all documents"),
        ('general', False, "General should NOT access engineering documents"),
    ]
    
    for role, should_have_access, description in test_cases:
        results = await self.vector_store.search_with_rbac(
            query="engineering system performance",
            user_role=role,
            limit=5
        )
        
        if should_have_access:
            assert len(results) > 0, f"RBAC FAIL: {description}"
            # Validate all results are accessible to role
            for chunk, score in results:
                assert role in chunk.metadata.access_roles, f"Role {role} not in access_roles"
        else:
            assert len(results) == 0, f"RBAC BREACH: {description}"
```

### Cross-Collection Security Test
```python
async def test_cross_collection_security(self):
    """Test security boundaries between collections"""
    # Ingest documents from multiple collections
    collections = ['engineering', 'finance', 'marketing', 'general']
    
    for collection in collections:
        # Test that users only see their authorized documents
        for role in ['engineering', 'finance', 'marketing', 'general', 'c_level']:
            results = await self.vector_store.search_with_rbac(
                query=f"{collection} documents",
                user_role=role,
                collection_filter=collection
            )
            
            # Validate RBAC enforcement
            for chunk, _ in results:
                assert role in chunk.metadata.access_roles, \
                    f"SECURITY BREACH: Role {role} accessed {collection} without permission"
```

## 📈 Performance Testing

### Response Time Benchmarks
```python
async def test_performance_benchmarks(self):
    """Measure system performance under various loads"""
    import time
    
    performance_results = {
        'document_processing': [],
        'vector_storage': [],
        'search_queries': [],
        'rbac_filtering': []
    }
    
    # Document processing performance
    for _ in range(10):
        start_time = time.time()
        doc = await self.processor.process_document(test_file, 'engineering')
        processing_time = time.time() - start_time
        performance_results['document_processing'].append(processing_time)
    
    # Search query performance  
    for query, _ in SEARCH_TEST_QUERIES:
        start_time = time.time()
        results = await self.vector_store.search_with_rbac(query, 'engineering')
        search_time = time.time() - start_time
        performance_results['search_queries'].append(search_time)
    
    # Report performance metrics
    for operation, times in performance_results.items():
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)
        
        print(f"{operation}:")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Range: {min_time:.3f}s - {max_time:.3f}s")
```

### Memory Usage Monitoring
```python
import psutil
import tracemalloc

async def test_memory_usage(self):
    """Monitor memory usage during operations"""
    tracemalloc.start()
    process = psutil.Process()
    
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    # Perform memory-intensive operations
    docs = []
    for _ in range(10):
        doc = await self.processor.process_document(large_test_file, 'engineering')
        docs.append(doc)
    
    peak_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    current, peak_trace = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    memory_increase = peak_memory - initial_memory
    
    # Assert reasonable memory usage
    assert memory_increase < 500, f"Memory usage too high: {memory_increase}MB"
    print(f"📊 Memory usage: +{memory_increase:.1f}MB (peak: {peak_memory:.1f}MB)")
```

## 🎯 Test Execution & Reporting

### Running Tests
```bash
# Run complete test suite
python src/tests/test_ingestion_and_search.py

# Run with verbose output
python src/tests/test_ingestion_and_search.py --verbose

# Run specific test categories
python -m pytest src/tests/ -k "rbac"
python -m pytest src/tests/ -k "performance"
```

### Test Report Generation
```python
class TestReporter:
    def __init__(self):
        self.results = []
        self.start_time = time.time()
    
    def add_result(self, test_name: str, status: str, duration: float, details: Dict = None):
        self.results.append({
            'test': test_name,
            'status': status,  # PASS, FAIL, SKIP
            'duration': duration,
            'details': details or {}
        })
    
    def generate_report(self) -> str:
        total_tests = len(self.results)
        passed = len([r for r in self.results if r['status'] == 'PASS'])
        failed = len([r for r in self.results if r['status'] == 'FAIL']) 
        
        report = f"""
🧪 FinBot Test Report
=====================
Total Tests: {total_tests}
Passed: {passed} ✅
Failed: {failed} ❌
Success Rate: {(passed/total_tests)*100:.1f}%
Total Duration: {time.time() - self.start_time:.2f}s

📊 Performance Summary:
• Document Processing: {self._avg_time('document_processing'):.3f}s avg
• Vector Storage: {self._avg_time('vector_storage'):.3f}s avg  
• Search Queries: {self._avg_time('search'):.3f}s avg
• RBAC Filtering: {self._avg_time('rbac'):.3f}s avg
"""
        return report
```

### Continuous Integration
```yaml
# GitHub Actions workflow
name: FinBot Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
    
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run tests
      run: python src/tests/test_ingestion_and_search.py
    
    - name: Generate coverage report
      run: pytest --cov=src --cov-report=xml
```

## 📋 Test Data & Fixtures

### Test Documents
```python
TEST_DOCUMENTS = {
    'engineering': 'data/engineering/system_sla_report_2024.md',
    'finance': 'data/finance/q4_financial_report.pdf',
    'marketing': 'data/marketing/campaign_analysis.docx',
    'general': 'data/general/company_handbook.md'
}

TEST_QUERIES = {
    'engineering': [
        "What are our SLA compliance targets?",
        "How is system performance measured?",
        "What are the error rates by service?"
    ],
    'finance': [
        "What was Q4 revenue growth?", 
        "What are the budget allocations?",
        "How did costs change year over year?"
    ]
}
```

### Mock Data Generation
```python
def generate_test_chunk(collection: str = 'engineering') -> DocumentChunk:
    """Generate mock document chunk for testing"""
    return DocumentChunk(
        headings=['Test Document', 'Test Section'],
        content='This is test content for validation purposes.',
        chunk_text='Test Document > Test Section\n\nThis is test content...',
        metadata=DocumentMetadata(
            collection=collection,
            access_roles=COLLECTION_ACCESS_ROLES[collection],
            source_document='test_document.md',
            document_path=f'tests/fixtures/{collection}/test_document.md'
        )
    )
```

## 🏗️ Testing Best Practices

### Test Organization
- **Integration focus**: Test complete workflows, not isolated units
- **Realistic scenarios**: Use actual documents and natural language queries  
- **Security emphasis**: RBAC testing is critical for production safety
- **Performance monitoring**: Track metrics to catch regressions

### Assertions & Validation
- **Structure validation**: Ensure data models match expectations
- **Business logic verification**: Validate RBAC rules and access patterns
- **Performance thresholds**: Assert reasonable response times
- **Error handling**: Test failure modes and edge cases

### Maintenance
- **Regular updates**: Keep test queries aligned with user patterns
- **Continuous monitoring**: Run tests on every code change
- **Documentation**: Update test docs when adding new test cases
- **Data freshness**: Regularly update test documents to reflect real usage

## 🎯 Success Criteria

### Functional Requirements ✅
- ✅ Document processing produces valid chunks with breadcrumbs
- ✅ Vector storage maintains 384D embeddings with metadata
- ✅ Search returns relevant results for natural language queries  
- ✅ RBAC enforcement blocks unauthorized access 100% of time

### Performance Requirements ✅  
- ✅ Document processing: < 1s per document (22KB)
- ✅ Search response time: < 200ms for typical queries
- ✅ Memory usage: < 500MB for batch operations
- ✅ Search accuracy: > 0.7 score for relevant queries

### Security Requirements ✅
- ✅ Zero cross-role data leakage in search results
- ✅ All chunks tagged with appropriate access roles
- ✅ RBAC filters applied before vector similarity search
- ✅ Access control validation for all user interactions