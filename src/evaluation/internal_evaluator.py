"""
Internal RAGAs-style evaluation metrics for FinBot
Implements evaluation metrics without external API dependencies
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional
import re
from collections import Counter
import statistics
import sys
import os

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.rag.rag_system import FinBotRAGSystem
from src.core.store.vector_store import VectorStore


logger = logging.getLogger(__name__)


class InternalEvaluator:
    """Internal evaluation system for FinBot with RAGAs-style metrics"""

    def __init__(
        self,
        test_dataset_path: str = "data/evaluation/test_dataset.json",
        role: Optional[str] = None,
    ):
        self.test_dataset_path = test_dataset_path
        # Label used in output filenames: specific role name or 'all'
        self.role_label = role if role else "all"
        self.rag_system = FinBotRAGSystem()
        self.vector_store = VectorStore()

        # Load test dataset
        self.test_cases = self._load_test_dataset()
        logger.info(
            f"Loaded {len(self.test_cases)} test cases "
            f"(role={self.role_label}, path={self.test_dataset_path})"
        )
    
    def _load_test_dataset(self) -> List[Dict[str, Any]]:
        """Load test dataset from JSON file"""
        try:
            with open(self.test_dataset_path, 'r') as f:
                data = json.load(f)
            return data.get('test_cases', [])
        except Exception as e:
            logger.error(f"Failed to load test dataset: {e}")
            return []
    
    def calculate_answer_relevancy(self, question: str, answer: str) -> float:
        """Calculate answer relevancy using keyword overlap and semantic indicators"""
        
        if not answer or answer.strip() == "":
            return 0.0
        
        # Extract keywords from question
        question_keywords = set(re.findall(r'\b\w+\b', question.lower()))
        question_keywords = {word for word in question_keywords if len(word) > 2}
        
        # Extract keywords from answer
        answer_keywords = set(re.findall(r'\b\w+\b', answer.lower()))
        answer_keywords = {word for word in answer_keywords if len(word) > 2}
        
        # Calculate keyword overlap
        if not question_keywords:
            return 0.5  # Default score if no keywords
        
        overlap = len(question_keywords.intersection(answer_keywords))
        keyword_score = overlap / len(question_keywords)
        
        # Check for answer quality indicators
        quality_indicators = {
            "specific_response": any(phrase in answer.lower() for phrase in [
                "based on", "according to", "the employee", "the document", "as stated"
            ]),
            "no_hedging": "i don't know" not in answer.lower() and "not sure" not in answer.lower(),
            "sufficient_length": len(answer.split()) >= 10,
            "contains_details": any(char.isdigit() for char in answer) or "FINEMP" in answer
        }
        
        quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        
        # Combine scores
        relevancy = (keyword_score * 0.6) + (quality_score * 0.4)
        return min(relevancy, 1.0)
    
    def calculate_faithfulness(self, answer: str, contexts: List[str]) -> float:
        """Calculate faithfulness by checking if answer content is supported by contexts"""
        
        if not answer or not contexts:
            return 0.0
        
        # Extract factual claims from answer
        claims = self._extract_claims(answer)
        
        if not claims:
            return 0.5  # Neutral score for non-factual answers
        
        # Check if claims are supported by contexts
        supported_claims = 0
        combined_context = " ".join(contexts).lower()
        
        for claim in claims:
            if self._is_claim_supported(claim, combined_context):
                supported_claims += 1
        
        faithfulness = supported_claims / len(claims) if claims else 0.0
        return faithfulness
    
    def calculate_context_precision(self, question: str, contexts: List[str], answer: str) -> float:
        """Calculate context precision - how useful were the retrieved contexts"""
        
        if not contexts:
            logger.warning("context_precision: NO CONTEXTS PROVIDED - returning 0.0")
            return 0.0
        
        question_keywords = set(re.findall(r'\b\w+\b', question.lower()))
        question_keywords = {w for w in question_keywords if len(w) > 2}
        answer_keywords = set(re.findall(r'\b\w+\b', answer.lower()))
        
        logger.debug(f"context_precision: Q_keywords={question_keywords} ({len(question_keywords)}), A_keywords count={len(answer_keywords)}")
        
        relevant_contexts = 0
        for i, context in enumerate(contexts, 1):
            context_keywords = set(re.findall(r'\b\w+\b', context.lower()))
            context_keywords = {w for w in context_keywords if len(w) > 2}
            
            question_overlap = len(question_keywords.intersection(context_keywords))
            answer_overlap = len(answer_keywords.intersection(context_keywords))
            relevance_score = (question_overlap + answer_overlap) / max(len(question_keywords), 1)
            
            logger.debug(f"  Context {i}: Q_overlap={question_overlap}, A_overlap={answer_overlap}, score={relevance_score:.3f}")
            if relevance_score > 0.3:
                relevant_contexts += 1
        
        precision = relevant_contexts / len(contexts)
        logger.debug(f"context_precision: {relevant_contexts}/{len(contexts)} = {precision:.3f}")
        return precision
    
    def calculate_context_recall(self, question: str, contexts: List[str], ground_truth: str) -> float:
        """Calculate context recall - did we retrieve all relevant information"""
        
        if not contexts or not ground_truth:
            return 0.0
        
        # Extract key concepts from ground truth
        gt_keywords = set(re.findall(r'\b\w+\b', ground_truth.lower()))
        gt_keywords = {word for word in gt_keywords if len(word) > 2}
        
        # Extract keywords from all contexts
        context_keywords = set()
        for context in contexts:
            context_words = set(re.findall(r'\b\w+\b', context.lower()))
            context_keywords.update(context_words)
        
        # Calculate recall
        if not gt_keywords:
            return 1.0  # Perfect recall if no specific requirements
        
        covered_concepts = len(gt_keywords.intersection(context_keywords))
        recall = covered_concepts / len(gt_keywords)
        
        return recall
    
    def calculate_answer_correctness(self, answer: str, ground_truth: str) -> float:
        """Calculate answer correctness compared to ground truth"""
        
        if not answer or not ground_truth:
            return 0.0
        
        # Normalize texts
        answer_norm = re.sub(r'\\s+', ' ', answer.lower().strip())
        gt_norm = re.sub(r'\\s+', ' ', ground_truth.lower().strip())
        
        # Extract key information
        answer_keywords = set(re.findall(r'\b\w+\b', answer_norm))
        gt_keywords = set(re.findall(r'\b\w+\b', gt_norm))
        
        # Filter out common words
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'as', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'shall'}
        answer_keywords = {word for word in answer_keywords if word not in common_words and len(word) > 2}
        gt_keywords = {word for word in gt_keywords if word not in common_words and len(word) > 2}
        
        # Calculate overlap
        if not gt_keywords:
            return 0.5  # Neutral score
        
        overlap = len(answer_keywords.intersection(gt_keywords))
        correctness = overlap / len(gt_keywords)
        
        # Boost score if specific entities match
        entity_boost = 0.0
        if "FINEMP" in answer and "FINEMP" in ground_truth:
            entity_boost += 0.2
        
        # Check for factual consistency
        if self._check_factual_consistency(answer, ground_truth):
            entity_boost += 0.1
        
        final_score = min(correctness + entity_boost, 1.0)
        return final_score
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text"""
        
        # Simple claim extraction based on sentence structure
        sentences = re.split(r'[.!?]+', text)
        claims = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
                
            # Look for factual statements
            if any(indicator in sentence.lower() for indicator in [
                'is', 'are', 'was', 'were', 'has', 'have', 'contains', 'includes',
                'id', 'name', 'department', 'salary', 'employee', 'finsolve'
            ]):
                claims.append(sentence)
        
        return claims
    
    def _is_claim_supported(self, claim: str, context: str) -> bool:
        """Check if a claim is supported by the context"""
        
        claim_words = set(re.findall(r'\b\w+\b', claim.lower()))
        context_words = set(re.findall(r'\b\w+\b', context.lower()))
        
        # High overlap suggests support
        overlap = len(claim_words.intersection(context_words))
        support_ratio = overlap / len(claim_words) if claim_words else 0
        
        return support_ratio > 0.5
    
    def _check_factual_consistency(self, answer: str, ground_truth: str) -> bool:
        """Check if answer is factually consistent with ground truth"""
        
        # Check for contradicting information
        answer_lower = answer.lower()
        gt_lower = ground_truth.lower()
        
        # Look for specific entity matches
        employee_ids_answer = re.findall(r'finemp\d+', answer_lower)
        employee_ids_gt = re.findall(r'finemp\d+', gt_lower)
        
        if employee_ids_answer and employee_ids_gt:
            return any(emp_id in employee_ids_gt for emp_id in employee_ids_answer)
        
        # Look for numerical consistency
        numbers_answer = re.findall(r'\b\d+\b', answer)
        numbers_gt = re.findall(r'\b\d+\b', ground_truth)
        
        if numbers_answer and numbers_gt:
            return any(num in numbers_gt for num in numbers_answer)
        
        return True  # No contradiction found
    
    async def evaluate_single_case(
        self,
        test_case: Dict[str, Any],
        config: Dict[str, bool],
        config_name: str = "Unknown",
    ) -> Dict[str, Any]:
        """Evaluate a single test case"""

        try:
            # Get system response
            if config.get('enable_full_system', True):
                result = await self.rag_system.process_query(
                    query=test_case['question'],
                    user_role=test_case['user_role'],
                    session_id=f"eval_{test_case['id']}"
                )
                answer = result.get('answer', '')
                confidence = result.get('confidence', 0.0)
            else:
                # Direct vector search
                search_results = await self.vector_store.search_with_rbac(
                    query=test_case['question'],
                    user_role=test_case['user_role'],
                    limit=5
                )

                if search_results:
                    answer = f"Based on available information: {search_results[0][0].content[:200]}..."
                    confidence = search_results[0][1]
                else:
                    answer = "No relevant information found."
                    confidence = 0.0

            # Get contexts (second search — for metric calculation)
            search_results = await self.vector_store.search_with_rbac(
                query=test_case['question'],
                user_role=test_case['user_role'],
                limit=5
            )
            contexts = [chunk.content for chunk, _ in search_results] if search_results else []

            # ── Detailed retrieval log ──────────────────────────────────────
            sep = "─" * 72
            logger.info(sep)
            logger.info(
                f"[Q{test_case['id']}] [{config_name}] "
                f"Role={test_case['user_role']} | Category={test_case.get('category', 'N/A')}"
            )
            logger.info(f"  QUESTION   : {test_case['question']}")
            logger.info(f"  GROUND TRUTH: {test_case['ground_truth']}")
            logger.info(f"  RETRIEVED CHUNKS ({len(search_results)} total):")
            if search_results:
                for rank, (chunk, score) in enumerate(search_results, 1):
                    src = getattr(chunk.metadata, 'source_document', 'unknown')
                    col = getattr(chunk.metadata, 'collection', 'unknown')
                    preview = chunk.content[:300].replace('\n', ' ')
                    logger.info(
                        f"    [{rank}] score={score:.4f} | src={src} | col={col}\n"
                        f"         content: {preview}{'...' if len(chunk.content) > 300 else ''}"
                    )
            else:
                logger.warning(f"    ⚠️  NO CHUNKS RETRIEVED — check Qdrant collection & RBAC filter")
            logger.info(f"  ANSWER     : {answer[:500].replace(chr(10), ' ')}{'...' if len(answer) > 500 else ''}")
            logger.info(sep)
            # ───────────────────────────────────────────────────────────────

            if not contexts:
                logger.warning(
                    f"[Q{test_case['id']}] NO CONTEXTS → faithfulness & context_precision will be 0"
                )
            
            # Calculate metrics
            metrics = {
                'faithfulness': self.calculate_faithfulness(answer, contexts),
                'answer_relevancy': self.calculate_answer_relevancy(test_case['question'], answer),
                'context_precision': self.calculate_context_precision(test_case['question'], contexts, answer),
                'context_recall': self.calculate_context_recall(test_case['question'], contexts, test_case['ground_truth']),
                'answer_correctness': self.calculate_answer_correctness(answer, test_case['ground_truth'])
            }
            
            return {
                'test_id': test_case['id'],
                'question': test_case['question'],
                'answer': answer,
                'ground_truth': test_case['ground_truth'],
                'collection': test_case['collection'],
                'user_role': test_case['user_role'],
                'category': test_case['category'],
                'confidence': confidence,
                'contexts_count': len(contexts),
                'metrics': metrics,
                'overall_score': sum(metrics.values()) / len(metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate test case {test_case['id']}: {e}")
            return {
                'test_id': test_case['id'],
                'question': test_case['question'],
                'error': str(e),
                'metrics': {metric: 0.0 for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'answer_correctness']},
                'overall_score': 0.0
            }
    
    async def run_evaluation(self, config_name: str, config: Dict[str, bool]) -> Dict[str, Any]:
        """Run evaluation on all test cases"""
        
        logger.info(f"\\n{'='*60}")
        logger.info(f"Running Evaluation: {config_name}")
        logger.info(f"Configuration: {config}")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        results = []
        
        # Process test cases in batches
        batch_size = 10
        for i in range(0, len(self.test_cases), batch_size):
            batch = self.test_cases[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(self.test_cases) + batch_size - 1)//batch_size}")
            
            batch_tasks = [
                self.evaluate_single_case(test_case, config, config_name=config_name)
                for test_case in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch evaluation error: {result}")
                    continue
                results.append(result)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        evaluation_time = time.time() - start_time
        
        # Calculate aggregate metrics
        valid_results = [r for r in results if 'error' not in r]
        
        if not valid_results:
            return {
                'config_name': config_name,
                'error': 'No valid results',
                'total_cases': len(self.test_cases)
            }
        
        # Aggregate scores
        metrics_summary = {}
        for metric in ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'answer_correctness']:
            scores = [r['metrics'][metric] for r in valid_results if 'metrics' in r]
            if scores:
                metrics_summary[metric] = {
                    'mean': statistics.mean(scores),
                    'median': statistics.median(scores),
                    'std': statistics.stdev(scores) if len(scores) > 1 else 0.0,
                    'min': min(scores),
                    'max': max(scores)
                }
        
        # Collection-wise analysis
        collection_analysis = {}
        for result in valid_results:
            collection = result['collection']
            if collection not in collection_analysis:
                collection_analysis[collection] = []
            collection_analysis[collection].append(result['overall_score'])
        
        for collection, scores in collection_analysis.items():
            collection_analysis[collection] = {
                'count': len(scores),
                'mean_score': statistics.mean(scores),
                'median_score': statistics.median(scores)
            }
        
        return {
            'config_name': config_name,
            'configuration': config,
            'evaluation_time_seconds': evaluation_time,
            'total_cases': len(self.test_cases),
            'valid_results': len(valid_results),
            'failed_results': len(results) - len(valid_results),
            'overall_score': statistics.mean([r['overall_score'] for r in valid_results]),
            'metrics_summary': metrics_summary,
            'collection_analysis': collection_analysis,
            'detailed_results': results,
            'timestamp': datetime.now().isoformat()
        }
    
    async def run_ablation_study(self) -> Dict[str, Any]:
        """Run comprehensive ablation study"""
        
        logger.info("🚀 Starting Internal RAGAs Evaluation Ablation Study")
        
        configurations = [
            {
                'name': 'Full System',
                'config': {'enable_full_system': True},
                'description': 'Complete FinBot with all components'
            },
            {
                'name': 'Direct Vector Search',
                'config': {'enable_full_system': False},
                'description': 'Direct vector search without RAG processing'
            }
        ]
        
        study_results = {}
        
        for config_info in configurations:
            result = await self.run_evaluation(config_info['name'], config_info['config'])
            result['description'] = config_info['description']
            study_results[config_info['name']] = result
        
        # Generate comparison
        if len(study_results) >= 2:
            study_results['comparison'] = self._generate_comparison(study_results)
        
        study_results['metadata'] = {
            'total_test_cases': len(self.test_cases),
            'completion_time': datetime.now().isoformat(),
            'evaluation_framework': 'Internal RAGAs-style metrics'
        }
        
        return study_results
    
    def _generate_comparison(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comparison between configurations"""
        
        configs = {k: v for k, v in results.items() if k not in ['comparison', 'metadata']}
        
        comparison = {
            'metric_comparison': {},
            'best_configuration': {},
            'performance_improvement': {}
        }
        
        # Find best config for each metric
        metric_names = ['faithfulness', 'answer_relevancy', 'context_precision', 'context_recall', 'answer_correctness']
        
        for metric in metric_names:
            best_config = None
            best_score = -1
            
            for config_name, config_result in configs.items():
                if 'metrics_summary' in config_result and metric in config_result['metrics_summary']:
                    score = config_result['metrics_summary'][metric]['mean']
                    if score > best_score:
                        best_score = score
                        best_config = config_name
            
            if best_config:
                comparison['best_configuration'][metric] = {'config': best_config, 'score': best_score}
        
        # Calculate improvements
        if 'Full System' in configs and 'Direct Vector Search' in configs:
            full_system = configs['Full System']
            direct_search = configs['Direct Vector Search']
            
            for metric in metric_names:
                if ('metrics_summary' in full_system and metric in full_system['metrics_summary'] and
                    'metrics_summary' in direct_search and metric in direct_search['metrics_summary']):
                    
                    full_score = full_system['metrics_summary'][metric]['mean']
                    direct_score = direct_search['metrics_summary'][metric]['mean']
                    
                    improvement = full_score - direct_score
                    percentage_improvement = (improvement / direct_score * 100) if direct_score > 0 else 0
                    
                    comparison['performance_improvement'][metric] = {
                        'absolute_improvement': improvement,
                        'percentage_improvement': percentage_improvement
                    }
        
        return comparison
    
    def save_results(self, results: Dict[str, Any]) -> str:
        """Save results to file"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Stamp filename with role label so per-role runs don't overwrite each other
        filepath = f"data/evaluation/internal_evaluation_{self.role_label}_{timestamp}.json"

        import os
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(f"Results saved to {filepath}")
        return filepath
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate evaluation report"""
        
        report_lines = [
            "# FinBot Internal Evaluation Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            ""
        ]
        
        if 'metadata' in results:
            metadata = results['metadata']
            report_lines.extend([
                f"- **Total Test Cases**: {metadata.get('total_test_cases', 'N/A')}",
                f"- **Evaluation Framework**: {metadata.get('evaluation_framework', 'N/A')}",
                f"- **Completion Time**: {metadata.get('completion_time', 'N/A')}",
                ""
            ])
        
        # Configuration results
        for config_name, config_result in results.items():
            if config_name in ['comparison', 'metadata']:
                continue
            
            if 'error' in config_result:
                report_lines.extend([
                    f"## {config_name}",
                    f"**Error**: {config_result['error']}",
                    ""
                ])
                continue
            
            report_lines.extend([
                f"## {config_name}",
                f"**Description**: {config_result.get('description', 'N/A')}",
                f"**Overall Score**: {config_result.get('overall_score', 0):.3f}",
                f"**Valid Results**: {config_result.get('valid_results', 0)}/{config_result.get('total_cases', 0)}",
                ""
            ])
            
            # Metrics
            if 'metrics_summary' in config_result:
                report_lines.append("### Metrics")
                for metric, stats in config_result['metrics_summary'].items():
                    report_lines.append(f"- **{metric}**: {stats['mean']:.3f} (±{stats['std']:.3f})")
                report_lines.append("")
            
            # Collection analysis
            if 'collection_analysis' in config_result:
                report_lines.append("### Collection Performance")
                for collection, stats in config_result['collection_analysis'].items():
                    report_lines.append(f"- **{collection}**: {stats['mean_score']:.3f} ({stats['count']} cases)")
                report_lines.append("")
        
        # Comparison
        if 'comparison' in results:
            comparison = results['comparison']
            report_lines.append("## Performance Comparison")
            
            if 'best_configuration' in comparison:
                report_lines.append("### Best Performing Configuration by Metric")
                for metric, best in comparison['best_configuration'].items():
                    report_lines.append(f"- **{metric}**: {best['config']} ({best['score']:.3f})")
                report_lines.append("")
            
            if 'performance_improvement' in comparison:
                report_lines.append("### Full System vs Direct Search")
                for metric, improvement in comparison['performance_improvement'].items():
                    abs_imp = improvement['absolute_improvement']
                    pct_imp = improvement['percentage_improvement']
                    report_lines.append(f"- **{metric}**: {abs_imp:+.3f} ({pct_imp:+.1f}%)")
                report_lines.append("")
        
        return "\\n".join(report_lines)


# Test runner function
async def run_internal_evaluation(
    dataset_path: str = "data/evaluation/test_dataset.json",
    role: Optional[str] = None,
):
    """
    Run the internal evaluation.

    Args:
        dataset_path: Path to the JSON test dataset to load.
        role: Human-readable role label (e.g. 'hr', 'finance').  Used to stamp
              the output filename.  Pass None when evaluating all roles.
    """

    # Only configure logging when run directly (no handlers set up by orchestrator yet)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    evaluator = InternalEvaluator(test_dataset_path=dataset_path, role=role)

    # Run ablation study
    results = await evaluator.run_ablation_study()

    # Save results
    results_file = evaluator.save_results(results)

    # Generate and display report
    report = evaluator.generate_report(results)
    print("\n" + "=" * 80)
    print(report)
    print("=" * 80)

    logger.info(f"✅ Evaluation completed! Results saved to: {results_file}")


if __name__ == "__main__":
    asyncio.run(run_internal_evaluation())