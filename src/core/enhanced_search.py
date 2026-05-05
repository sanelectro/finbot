"""
Enhanced search functionality that combines semantic search with numerical reasoning
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from src.core.vector_store import VectorStore
from src.models.document import DocumentChunk, Role

logger = logging.getLogger(__name__)

class EnhancedSearchEngine:
    """
    Enhanced search engine that handles both semantic and numerical queries
    """
    
    def __init__(self):
        self.vector_store = VectorStore()
        
        # Query patterns that require numerical processing
        self.salary_patterns = [
            r'highest.*salary',
            r'maximum.*salary', 
            r'top.*paid',
            r'best.*paid',
            r'most.*earning',
            r'richest.*employee'
        ]
    
    def _is_salary_query(self, query: str) -> bool:
        """Detect if query is asking for salary-based ranking"""
        query_lower = query.lower()
        return any(re.search(pattern, query_lower) for pattern in self.salary_patterns)
    
    async def search_with_intelligence(
        self,
        query: str,
        user_role: Role,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Intelligent search that chooses appropriate strategy based on query type
        
        Args:
            query: User's search query
            user_role: User's role for RBAC
            limit: Maximum results to return
            
        Returns:
            Enhanced search results with metadata
        """
        
        if self._is_salary_query(query):
            logger.info(f"Detected salary query: {query}")
            return await self._salary_based_search(query, user_role, limit)
        else:
            # Regular semantic search
            logger.info(f"Using semantic search for: {query}")
            results = await self.vector_store.search_with_rbac(query, user_role, limit)
            return {
                "query": query,
                "search_type": "semantic",
                "results": results,
                "total_results": len(results)
            }
    
    async def _salary_based_search(
        self,
        query: str,
        user_role: Role,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Handle salary-based queries with numerical ranking
        
        Strategy:
        1. Cast wide semantic net with salary-related terms
        2. Extract salary data from all results
        3. Sort by actual salary amounts
        4. Return top results by salary, not semantic similarity
        """
        
        # Step 1: Get broad set of employee records using salary-related terms
        broad_results = await self.vector_store.search_with_rbac(
            "employee salary compensation annual", 
            user_role, 
            limit=100  # Cast wide net
        )
        
        # Step 2: Extract and structure salary data
        salary_employees = []
        
        for chunk, semantic_score in broad_results:
            # Extract employee data from natural language format
            # Pattern: "Employee Name (ID: FINEMP1234) works as..."
            id_pattern = r'Employee [^(]+ \(ID: (FINEMP\d+)\)'
            id_match = re.search(id_pattern, chunk.content)
            
            if id_match:
                emp_id = id_match.group(1)
                
                # Extract name: "Employee Name (ID:" 
                name_pattern = r'Employee ([^(]+) \(ID:'
                name_match = re.search(name_pattern, chunk.content)
                
                # Extract salary: "Annual compensation: 123456"
                salary_pattern = r'Annual compensation: (\d+)'
                salary_match = re.search(salary_pattern, chunk.content)
                
                # Extract role: "works as a Role in Department"
                role_pattern = r'works as a ([^.]+?) in the ([^.]+?) department'
                role_match = re.search(role_pattern, chunk.content)
                
                if salary_match and name_match:
                    salary = int(salary_match.group(1))
                    name = name_match.group(1).strip()
                    role = role_match.group(1).strip() if role_match else "Unknown"
                    department = role_match.group(2).strip() if role_match else "Unknown"
                    
                    salary_employees.append({
                        'chunk': chunk,
                        'emp_id': emp_id,
                        'name': name,
                        'role': role,
                        'department': department,
                        'salary': salary,
                        'semantic_score': semantic_score
                    })
        
        # Step 3: Sort by actual salary (highest first)
        salary_employees.sort(key=lambda x: x['salary'], reverse=True)
        
        # Step 4: Return top results with enhanced metadata
        top_results = salary_employees[:limit]
        
        # Convert back to (chunk, score) format but use salary-based ranking
        final_results = []
        for i, emp in enumerate(top_results):
            # Create a hybrid score that prioritizes salary ranking
            salary_rank_score = 1.0 - (i / max(len(salary_employees), 1))  # 1.0 for highest, decreasing
            final_results.append((emp['chunk'], salary_rank_score))
        
        return {
            "query": query,
            "search_type": "salary_ranking",
            "results": final_results,
            "total_results": len(final_results),
            "metadata": {
                "highest_salary": top_results[0]['salary'] if top_results else 0,
                "salary_range": {
                    "min": min(emp['salary'] for emp in salary_employees) if salary_employees else 0,
                    "max": max(emp['salary'] for emp in salary_employees) if salary_employees else 0
                },
                "employees_analyzed": len(salary_employees)
            }
        }


# Convenience function for testing
async def test_enhanced_search():
    """Test the enhanced search functionality"""
    engine = EnhancedSearchEngine()
    
    test_queries = [
        "Who has the highest salary?",
        "Top 3 highest paid employees",
        "Maximum salary employee",
        "Employee with best compensation"
    ]
    
    for query in test_queries:
        print(f"\\n{'='*60}")
        print(f"Query: {query}")
        print('='*60)
        
        result = await engine.search_with_intelligence(query, "hr", limit=5)
        
        print(f"Search Type: {result['search_type']}")
        print(f"Total Results: {result['total_results']}")
        
        if 'metadata' in result:
            meta = result['metadata']
            print(f"Employees Analyzed: {meta['employees_analyzed']}")
            print(f"Salary Range: {meta['salary_range']['min']:,} - {meta['salary_range']['max']:,}")
        
        print("\\nTop Results:")
        for i, (chunk, score) in enumerate(result['results']):
            # Extract data from natural language format
            emp_id_match = re.search(r'Employee [^(]+ \(ID: (FINEMP\d+)\)', chunk.content)
            name_match = re.search(r'Employee ([^(]+) \(ID:', chunk.content)
            salary_match = re.search(r'Annual compensation: (\d+)', chunk.content)
            
            emp_id = emp_id_match.group(1) if emp_id_match else "N/A"
            name = name_match.group(1).strip() if name_match else "N/A" 
            salary = int(salary_match.group(1)) if salary_match else 0
            
            print(f"{i+1}. {emp_id} - {name} - Salary: {salary:,} (Score: {score:.4f})")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_enhanced_search())