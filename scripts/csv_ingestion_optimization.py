"""
Best Practices for CSV Employee Data Ingestion for Accurate Semantic Search
"""

import pandas as pd
import re
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass 
class EnhancedEmployee:
    """Enhanced employee record with semantic optimization"""
    employee_id: str
    name: str
    salary: int
    role: str
    department: str
    original_data: dict
    
    def generate_semantic_content(self) -> str:
        """Generate semantically rich content for better search accuracy"""
        
        # 1. Add salary ranking context
        salary_tier = self._get_salary_tier(self.salary)
        compensation_terms = self._get_compensation_terms(self.salary)
        
        # 2. Generate query-oriented content
        content_parts = []
        
        # Basic employee information
        content_parts.append(f"Employee Data Record for {self.employee_id}")
        content_parts.append(f"Name: {self.name}")
        content_parts.append(f"Position: {self.role} in {self.department} department")
        
        # Enhanced salary context with semantic richness
        content_parts.append(f"Compensation: ${self.salary:,} annual salary")
        content_parts.append(f"Salary Tier: {salary_tier}")
        content_parts.append(f"Compensation Level: {compensation_terms}")
        
        # Add query-matching phrases
        if self.salary > 5000000:  # Top 10% threshold
            content_parts.append("Classification: High-earning employee, top salary range, maximum compensation tier")
        elif self.salary > 3000000:  # Top 25% threshold  
            content_parts.append("Classification: Well-compensated employee, upper salary range")
        elif self.salary > 1500000:  # Median threshold
            content_parts.append("Classification: Competitive salary, mid-range compensation")
        else:
            content_parts.append("Classification: Standard salary range")
        
        # Add searchable terms that match common queries
        search_context = []
        search_context.extend([
            f"{self.name} employee record",
            f"{self.employee_id} staff information", 
            f"{self.role} {self.department}",
            f"salary {self.salary}",
            f"compensation data",
            f"employee earnings information"
        ])
        
        if self.salary > 5000000:
            search_context.extend([
                "highest paid employee",
                "maximum salary employee", 
                "top earning staff member",
                "best compensated employee",
                "highest compensation",
                "top salary employee"
            ])
        
        content_parts.append(f"Search Keywords: {', '.join(search_context)}")
        
        return "\\n".join(content_parts)
    
    def _get_salary_tier(self, salary: int) -> str:
        """Classify salary into semantic tiers"""
        if salary >= 6000000:
            return "Executive/Top-Tier (6M+)"
        elif salary >= 4000000:
            return "Senior Management (4-6M)"
        elif salary >= 2000000:
            return "Management Level (2-4M)"  
        elif salary >= 1000000:
            return "Professional Level (1-2M)"
        else:
            return "Entry/Mid Level (<1M)"
    
    def _get_compensation_terms(self, salary: int) -> str:
        """Generate semantic terms for salary ranges"""
        if salary >= 6000000:
            return "Premium compensation, executive pay scale, top-tier earnings"
        elif salary >= 4000000:
            return "High compensation, senior management pay, excellent salary"
        elif salary >= 2000000:
            return "Above-average compensation, management-level pay"
        elif salary >= 1000000:
            return "Competitive compensation, professional-level pay"
        else:
            return "Standard compensation, entry to mid-level pay"


class OptimizedCSVIngestion:
    """Optimized CSV ingestion for semantic search accuracy"""
    
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
        self.salary_percentiles = self._calculate_salary_percentiles()
    
    def _calculate_salary_percentiles(self) -> Dict[str, float]:
        """Calculate salary percentiles for contextual ranking"""
        return {
            'p90': self.df['salary'].quantile(0.9),
            'p75': self.df['salary'].quantile(0.75), 
            'p50': self.df['salary'].quantile(0.5),
            'p25': self.df['salary'].quantile(0.25)
        }
    
    def generate_enhanced_records(self) -> List[EnhancedEmployee]:
        """Generate enhanced employee records optimized for semantic search"""
        
        enhanced_employees = []
        
        for _, row in self.df.iterrows():
            emp = EnhancedEmployee(
                employee_id=row['employee_id'],
                name=row['full_name'],
                salary=int(row['salary']) if pd.notna(row['salary']) else 0,
                role=row['role'],
                department=row['department'],
                original_data=row.to_dict()
            )
            
            enhanced_employees.append(emp)
        
        return enhanced_employees
    
    def demonstrate_improvement(self):
        """Show before/after comparison of ingestion approaches"""
        
        print("=== CSV INGESTION OPTIMIZATION FOR SEMANTIC SEARCH ===\\n")
        
        # Get highest salary employee
        top_employee = self.df.loc[self.df['salary'].idxmax()]
        
        print("🔍 CASE STUDY: Highest Salary Employee")
        print(f"Employee: {top_employee['employee_id']} - {top_employee['full_name']}")
        print(f"Salary: ${top_employee['salary']:,.0f}")
        print()
        
        # Show current vs optimized content
        print("❌ CURRENT INGESTION (Poor Semantic Matching):")
        print("-" * 50)
        current_content = f"""Employee ID: {top_employee['employee_id']}
Full Name: {top_employee['full_name']}
Role: {top_employee['role']}
Department: {top_employee['department']}
Salary: {top_employee['salary']}"""
        print(current_content)
        print()
        
        # Generate enhanced version
        enhanced_emp = EnhancedEmployee(
            employee_id=str(top_employee['employee_id']),
            name=str(top_employee['full_name']),
            salary=int(top_employee['salary'].item()) if pd.notna(top_employee['salary'].item()) else 0,
            role=str(top_employee['role']),
            department=str(top_employee['department']),
            original_data=top_employee.to_dict()
        )
        
        print("✅ OPTIMIZED INGESTION (Rich Semantic Context):")
        print("-" * 50)
        optimized_content = enhanced_emp.generate_semantic_content()
        print(optimized_content)
        print()
        
        print("🎯 KEY IMPROVEMENTS:")
        print("1. ✅ Added salary tier classifications")
        print("2. ✅ Included query-matching phrases ('highest paid', 'maximum salary')")
        print("3. ✅ Rich compensation context with semantic terms")
        print("4. ✅ Explicit ranking indicators (Top-Tier, Executive)")
        print("5. ✅ Search keywords for common query patterns")
        print()
        
        print("📈 EXPECTED RESULTS:")
        print("• Better matching for 'highest salary employee' queries")
        print("• Improved ranking for compensation-related searches")  
        print("• More accurate semantic similarity scores")
        print("• Enhanced context for LLM understanding")


# Demonstration
if __name__ == "__main__":
    print("Analyzing current CSV ingestion and proposing optimizations...\\n")
    
    optimizer = OptimizedCSVIngestion('data/hr/hr_data.csv')
    optimizer.demonstrate_improvement()
    
    print("\\n" + "="*60)
    print("💡 IMPLEMENTATION RECOMMENDATIONS:")
    print("="*60)
    print()
    print("1. ROW-LEVEL ENHANCEMENT:")
    print("   • Each employee = separate semantic chunk")
    print("   • Add salary tier classifications") 
    print("   • Include ranking/superlative terms")
    print()
    print("2. QUERY-ORIENTED CONTENT:")
    print("   • Add phrases that match common queries")
    print("   • Include 'highest paid', 'maximum salary', 'top earnings'")
    print("   • Semantic context for numerical values")
    print()
    print("3. HYBRID METADATA:")
    print("   • Store numerical salary for direct filtering")
    print("   • Semantic content for embedding similarity")
    print("   • Structured data for exact matching")
    print()
    print("4. NUMERICAL CONTEXT:")
    print("   • Convert numbers to semantic ranges")
    print("   • Add comparative terms (above-average, top-tier)")
    print("   • Include percentile classifications")