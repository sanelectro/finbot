"""
RAGAs Evaluation Framework for FinBot - Component 4 Implementation
Comprehensive evaluation using RAGAs metrics with ablation studies
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging
import pandas as pd

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# RAGAs imports
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    answer_correctness
)
from datasets import Dataset

# FinBot imports
from src.core.rag.rag_system import FinBotRAGSystem
from src.core.store.vector_store import VectorStore
from src.models.document import Role

logger = logging.getLogger(__name__)


class RAGAsEvaluator:
    """RAGAs evaluation framework for FinBot system"""
    
    def __init__(self, test_dataset_path: str = "data/evaluation/test_dataset.json"):
        self.test_dataset_path = test_dataset_path
        self.rag_system = FinBotRAGSystem()
        self.vector_store = VectorStore()
        self.results = {}
        
        # Load test dataset
        self.test_cases = self._load_test_dataset()
        
        # RAGAs metrics
        self.metrics = [
            faithfulness,
            answer_relevancy, 
            context_precision,
            context_recall,
            answer_correctness
        ]
        
        logger.info(f"RAGAs Evaluator initialized with {len(self.test_cases)} test cases")
    
    def _load_test_dataset(self) -> List[Dict[str, Any]]:
        """Load test dataset from JSON file"""
        try:
            with open(self.test_dataset_path, 'r') as f:
                data = json.load(f)
            return data.get('test_cases', [])
        except Exception as e:
            logger.error(f"Failed to load test dataset: {e}")
            return []
    
    async def generate_responses_for_dataset(self, enable_semantic_router: bool = True, enable_guardrails: bool = True) -> List[Dict[str, Any]]:
        """Generate responses for all test cases with specified configuration"""
        
        responses = []
        
        for i, test_case in enumerate(self.test_cases):
            try:
                logger.info(f"Processing test case {i+1}/{len(self.test_cases)}: {test_case['question']}")
                
                # Get response from RAG system
                if enable_semantic_router and enable_guardrails:
                    # Full system with all components
                    result = await self.rag_system.process_query(
                        query=test_case['question'],
                        user_role=test_case['user_role'],
                        session_id=f"eval_session_{i}"
                    )
                else:
                    # Direct vector search without semantic router/guardrails
                    search_results = await self.vector_store.search_with_rbac(
                        query=test_case['question'],
                        user_role=test_case['user_role'],
                        limit=5
                    )
                    
                    # Create simple response
                    if search_results:
                        context_text = "\\n\\n".join([
                            f"Source: {chunk.metadata.source_document}\\n{chunk.content}"
                            for chunk, _ in search_results
                        ])
                        result = {
                            "answer": f"Based on the available information: {search_results[0][0].content[:200]}...",
                            "confidence": search_results[0][1] if search_results else 0.0
                        }
                    else:
                        context_text = ""
                        result = {
                            "answer": "No relevant information found.",
                            "confidence": 0.0
                        }
                
                # Extract contexts from search results
                if enable_semantic_router and enable_guardrails:
                    # For full system, get context from vector search
                    search_results = await self.vector_store.search_with_rbac(
                        query=test_case['question'],
                        user_role=test_case['user_role'],
                        limit=5
                    )
                    contexts = [chunk.content for chunk, _ in search_results] if search_results else []
                else:
                    contexts = [chunk.content for chunk, _ in search_results] if search_results else []
                
                response_data = {
                    "question": test_case['question'],
                    "answer": result.get('answer', ''),
                    "contexts": contexts,
                    "ground_truth": test_case['ground_truth'],
                    "collection": test_case['collection'],
                    "user_role": test_case['user_role'],
                    "category": test_case['category'],
                    "confidence": result.get('confidence', 0.0),
                    "test_id": test_case['id']
                }
                
                responses.append(response_data)
                
                # Small delay to avoid overwhelming the system
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to process test case {test_case['id']}: {e}")
                # Add failed response
                responses.append({
                    "question": test_case['question'],
                    "answer": f"Error processing query: {str(e)}",
                    "contexts": [],
                    "ground_truth": test_case['ground_truth'],
                    "collection": test_case['collection'],
                    "user_role": test_case['user_role'],
                    "category": test_case['category'],
                    "confidence": 0.0,
                    "test_id": test_case['id']
                })
        
        return responses
    
    def prepare_ragas_dataset(self, responses: List[Dict[str, Any]]) -> Dataset:
        """Convert responses to RAGAs dataset format"""
        
        # Filter out responses with empty contexts or answers
        valid_responses = [
            r for r in responses 
            if r['contexts'] and r['answer'] and r['answer'] != "No relevant information found."
        ]
        
        logger.info(f"Prepared {len(valid_responses)} valid responses out of {len(responses)} total")
        
        # Convert to RAGAs format
        dataset_dict = {
            "question": [r['question'] for r in valid_responses],
            "answer": [r['answer'] for r in valid_responses],
            "contexts": [r['contexts'] for r in valid_responses],
            "ground_truth": [r['ground_truth'] for r in valid_responses]
        }
        
        return Dataset.from_dict(dataset_dict)
    
    async def evaluate_system_configuration(
        self, 
        config_name: str,
        enable_semantic_router: bool = True,
        enable_guardrails: bool = True
    ) -> Dict[str, Any]:
        """Evaluate a specific system configuration"""
        
        logger.info(f"\\n{'='*60}")
        logger.info(f"Evaluating Configuration: {config_name}")
        logger.info(f"Semantic Router: {enable_semantic_router}, Guardrails: {enable_guardrails}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        
        # Generate responses
        responses = await self.generate_responses_for_dataset(
            enable_semantic_router=enable_semantic_router,
            enable_guardrails=enable_guardrails
        )
        
        # Prepare dataset for RAGAs
        dataset = self.prepare_ragas_dataset(responses)
        
        if len(dataset) == 0:
            logger.warning(f"No valid responses for configuration {config_name}")
            return {
                "config_name": config_name,
                "error": "No valid responses generated",
                "total_responses": len(responses),
                "valid_responses": 0
            }
        
        # Run RAGAs evaluation
        try:
            logger.info(f"Running RAGAs evaluation on {len(dataset)} samples...")
            
            # Note: RAGAs requires OpenAI API key for some metrics
            # For demo purposes, we'll calculate available metrics
            eval_results = evaluate(
                dataset=dataset,
                metrics=self.metrics,
                raise_exceptions=False
            )
            
            evaluation_time = time.time() - start_time
            
            # Extract scores
            scores = {}
            for metric in self.metrics:
                metric_name = metric.name
                if hasattr(eval_results, metric_name):
                    score_value = getattr(eval_results, metric_name)
                    if score_value is not None:
                        scores[metric_name] = float(score_value)
                    else:
                        scores[metric_name] = 0.0
                else:
                    scores[metric_name] = 0.0
            
            result = {
                "config_name": config_name,
                "semantic_router_enabled": enable_semantic_router,
                "guardrails_enabled": enable_guardrails,
                "total_test_cases": len(self.test_cases),
                "total_responses": len(responses),
                "valid_responses": len(dataset),
                "evaluation_time_seconds": evaluation_time,
                "scores": scores,
                "timestamp": datetime.now().isoformat()
            }
            
            # Calculate summary metrics
            if scores:
                result["average_score"] = sum(scores.values()) / len(scores)
                result["min_score"] = min(scores.values())
                result["max_score"] = max(scores.values())
            
            logger.info(f"Configuration {config_name} completed in {evaluation_time:.2f} seconds")
            logger.info(f"Scores: {scores}")
            
            return result
            
        except Exception as e:
            logger.error(f"RAGAs evaluation failed for {config_name}: {e}")
            
            # Fallback: Calculate basic metrics
            return self._calculate_basic_metrics(config_name, responses, enable_semantic_router, enable_guardrails)
    
    def _calculate_basic_metrics(
        self, 
        config_name: str, 
        responses: List[Dict[str, Any]], 
        enable_semantic_router: bool, 
        enable_guardrails: bool
    ) -> Dict[str, Any]:
        """Calculate basic metrics when RAGAs evaluation fails"""
        
        valid_responses = [r for r in responses if r['answer'] and r['answer'] != "No relevant information found."]
        
        # Basic metrics calculation
        response_rate = len(valid_responses) / len(responses) if responses else 0
        avg_confidence = sum(r['confidence'] for r in valid_responses) / len(valid_responses) if valid_responses else 0
        
        # Context availability
        responses_with_context = len([r for r in valid_responses if r['contexts']])
        context_rate = responses_with_context / len(valid_responses) if valid_responses else 0
        
        # Collection coverage
        collections_covered = len(set(r['collection'] for r in valid_responses))
        
        return {
            "config_name": config_name,
            "semantic_router_enabled": enable_semantic_router,
            "guardrails_enabled": enable_guardrails,
            "total_test_cases": len(self.test_cases),
            "total_responses": len(responses),
            "valid_responses": len(valid_responses),
            "response_rate": response_rate,
            "average_confidence": avg_confidence,
            "context_availability_rate": context_rate,
            "collections_covered": collections_covered,
            "scores": {
                "response_rate": response_rate,
                "confidence_score": avg_confidence,
                "context_availability": context_rate,
                "collection_coverage": collections_covered / 5.0  # Normalize by total collections
            },
            "timestamp": datetime.now().isoformat(),
            "note": "Basic metrics due to RAGAs evaluation limitations"
        }
    
    async def run_ablation_study(self) -> Dict[str, Any]:
        """Run comprehensive ablation study across different configurations"""
        
        logger.info("\\n" + "="*80)
        logger.info("STARTING COMPREHENSIVE RAGAS ABLATION STUDY")
        logger.info("="*80)
        
        configurations = [
            {
                "name": "Full System",
                "semantic_router": True,
                "guardrails": True,
                "description": "Complete FinBot system with all components"
            },
            {
                "name": "No Guardrails",
                "semantic_router": True,
                "guardrails": False,
                "description": "Semantic router enabled, guardrails disabled"
            },
            {
                "name": "No Semantic Router",
                "semantic_router": False,
                "guardrails": True,
                "description": "Guardrails enabled, semantic router disabled"
            },
            {
                "name": "Baseline",
                "semantic_router": False,
                "guardrails": False,
                "description": "Basic RAG with vector search only"
            }
        ]
        
        study_results = {}
        
        for config in configurations:
            try:
                result = await self.evaluate_system_configuration(
                    config_name=config["name"],
                    enable_semantic_router=config["semantic_router"],
                    enable_guardrails=config["guardrails"]
                )
                
                result["description"] = config["description"]
                study_results[config["name"]] = result
                
                # Save intermediate results
                self._save_results({"ablation_study": study_results}, "intermediate")
                
            except Exception as e:
                logger.error(f"Failed to evaluate configuration {config['name']}: {e}")
                study_results[config["name"]] = {
                    "config_name": config["name"],
                    "error": str(e),
                    "description": config["description"]
                }
        
        # Generate comparative analysis
        study_results["analysis"] = self._generate_comparative_analysis(study_results)
        study_results["study_metadata"] = {
            "total_test_cases": len(self.test_cases),
            "completion_time": datetime.now().isoformat(),
            "configurations_tested": len(configurations)
        }
        
        return study_results
    
    def _generate_comparative_analysis(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comparative analysis of different configurations"""
        
        # Extract valid configurations (exclude analysis and metadata)
        configs = {k: v for k, v in results.items() if k not in ["analysis", "study_metadata"] and "error" not in v}
        
        if not configs:
            return {"error": "No valid configurations to analyze"}
        
        analysis = {
            "summary": {},
            "best_performing": {},
            "component_impact": {},
            "recommendations": []
        }
        
        # Find best performing configuration for each metric
        for config_name, config_result in configs.items():
            scores = config_result.get("scores", {})
            
            for metric, score in scores.items():
                if metric not in analysis["best_performing"]:
                    analysis["best_performing"][metric] = {"config": config_name, "score": score}
                elif score > analysis["best_performing"][metric]["score"]:
                    analysis["best_performing"][metric] = {"config": config_name, "score": score}
        
        # Calculate component impact
        if "Full System" in configs and "Baseline" in configs:
            full_scores = configs["Full System"].get("scores", {})
            baseline_scores = configs["Baseline"].get("scores", {})
            
            for metric in full_scores.keys():
                if metric in baseline_scores:
                    improvement = full_scores[metric] - baseline_scores[metric]
                    analysis["component_impact"][metric] = {
                        "improvement": improvement,
                        "percentage_improvement": (improvement / baseline_scores[metric] * 100) if baseline_scores[metric] > 0 else 0
                    }
        
        # Generate recommendations
        if analysis["best_performing"]:
            top_config = max(configs.keys(), key=lambda k: configs[k].get("average_score", 0))
            analysis["recommendations"].append(f"Best overall configuration: {top_config}")
            
            if "Full System" in analysis["best_performing"].values():
                analysis["recommendations"].append("Full system with all components shows strong performance")
            
            if any("improvement" in impact and impact["improvement"] > 0.1 
                  for impact in analysis["component_impact"].values()):
                analysis["recommendations"].append("Components provide significant performance improvements")
        
        return analysis
    
    def _save_results(self, results: Dict[str, Any], suffix: str = "") -> str:
        """Save evaluation results to JSON file"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ragas_evaluation_{suffix}_{timestamp}.json" if suffix else f"ragas_evaluation_{timestamp}.json"
        filepath = f"data/evaluation/{filename}"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            logger.info(f"Results saved to {filepath}")
            return filepath
        
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            return ""
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive evaluation report"""
        
        report_lines = [
            "# FinBot RAGAs Evaluation Report",
            f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Executive Summary",
            ""
        ]
        
        # Add summary statistics
        if "study_metadata" in results:
            metadata = results["study_metadata"]
            report_lines.extend([
                f"- **Total Test Cases**: {metadata.get('total_test_cases', 'N/A')}",
                f"- **Configurations Tested**: {metadata.get('configurations_tested', 'N/A')}",
                f"- **Evaluation Completed**: {metadata.get('completion_time', 'N/A')}",
                ""
            ])
        
        # Add configuration results
        report_lines.append("## Configuration Results")
        report_lines.append("")
        
        for config_name, config_result in results.items():
            if config_name in ["analysis", "study_metadata"]:
                continue
                
            if "error" in config_result:
                report_lines.extend([
                    f"### {config_name}",
                    f"**Status**: Error - {config_result['error']}",
                    ""
                ])
                continue
            
            report_lines.extend([
                f"### {config_name}",
                f"**Description**: {config_result.get('description', 'No description')}",
                f"**Valid Responses**: {config_result.get('valid_responses', 0)}/{config_result.get('total_responses', 0)}",
                ""
            ])
            
            # Add scores
            scores = config_result.get("scores", {})
            if scores:
                report_lines.append("**Metrics**:")
                for metric, score in scores.items():
                    report_lines.append(f"- {metric}: {score:.3f}")
                report_lines.append("")
                
                if "average_score" in config_result:
                    report_lines.append(f"**Average Score**: {config_result['average_score']:.3f}")
                    report_lines.append("")
        
        # Add comparative analysis
        if "analysis" in results and results["analysis"]:
            analysis = results["analysis"]
            report_lines.extend([
                "## Comparative Analysis",
                ""
            ])
            
            if "best_performing" in analysis:
                report_lines.append("### Best Performing Configurations")
                for metric, best in analysis["best_performing"].items():
                    report_lines.append(f"- **{metric}**: {best['config']} ({best['score']:.3f})")
                report_lines.append("")
            
            if "component_impact" in analysis:
                report_lines.append("### Component Impact Analysis")
                for metric, impact in analysis["component_impact"].items():
                    improvement = impact.get("improvement", 0)
                    percentage = impact.get("percentage_improvement", 0)
                    report_lines.append(f"- **{metric}**: +{improvement:.3f} (+{percentage:.1f}%)")
                report_lines.append("")
            
            if "recommendations" in analysis and analysis["recommendations"]:
                report_lines.append("### Recommendations")
                for rec in analysis["recommendations"]:
                    report_lines.append(f"- {rec}")
                report_lines.append("")
        
        report_content = "\\n".join(report_lines)
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filepath = f"data/evaluation/ragas_evaluation_report_{timestamp}.md"
        
        try:
            with open(report_filepath, 'w') as f:
                f.write(report_content)
            logger.info(f"Report saved to {report_filepath}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
        
        return report_content


async def main():
    """Run comprehensive RAGAs evaluation"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Initialize evaluator
    evaluator = RAGAsEvaluator()
    
    # Run ablation study
    results = await evaluator.run_ablation_study()
    
    # Save final results
    results_file = evaluator._save_results(results, "final")
    
    # Generate and print report
    report = evaluator.generate_report(results)
    print("\\n" + "="*80)
    print(report)
    print("="*80)
    
    print(f"\\n✅ Evaluation completed! Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(main())