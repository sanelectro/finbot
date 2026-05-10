#!/usr/bin/env python3
"""
Component 4: RAGAs Evaluation Implementation
Comprehensive evaluation runner for FinBot system

Usage:
    # Evaluate all roles (uses data/evaluation/test_dataset.json)
    python -m src.evaluation.ragas_orchestrator

    # Evaluate a specific role (uses data/evaluation/roles/<role>.json)
    python -m src.evaluation.ragas_orchestrator --role hr
    python -m src.evaluation.ragas_orchestrator --role finance
    python -m src.evaluation.ragas_orchestrator --role engineering
    python -m src.evaluation.ragas_orchestrator --role marketing
    python -m src.evaluation.ragas_orchestrator --role employee
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import datetime

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.evaluation.internal_evaluator import run_internal_evaluation

VALID_ROLES = ["hr", "finance", "engineering", "marketing", "employee"]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="FinBot RAGAs Evaluation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Evaluate all roles:
    python -m src.evaluation.ragas_orchestrator

  Evaluate only HR role:
    python -m src.evaluation.ragas_orchestrator --role hr

  Evaluate only Finance role:
    python -m src.evaluation.ragas_orchestrator --role finance
        """
    )
    parser.add_argument(
        "--role",
        type=str,
        choices=VALID_ROLES,
        default=None,
        help=(
            f"Evaluate a specific role only. "
            f"Choices: {', '.join(VALID_ROLES)}. "
            f"If omitted, all roles are evaluated using the full test dataset."
        )
    )
    return parser.parse_args()


async def main():
    """Main evaluation entry point"""

    args = parse_args()
    role = args.role

    print("""
██████╗  █████╗  ██████╗  █████╗ ███████╗    ███████╗██╗   ██╗ █████╗ ██╗     
██╔══██╗██╔══██╗██╔════╝ ██╔══██╗██╔════╝    ██╔════╝██║   ██║██╔══██╗██║     
██████╔╝███████║██║  ███╗███████║███████╗    █████╗  ██║   ██║███████║██║     
██╔══██╗██╔══██║██║   ██║██╔══██║╚════██║    ██╔══╝  ╚██╗ ██╔╝██╔══██║██║     
██║  ██║██║  ██║╚██████╔╝██║  ██║███████║    ███████╗ ╚████╔╝ ██║  ██║███████╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝    ╚══════╝  ╚═══╝  ╚═╝  ╚═╝╚══════╝
                                                                              
        Component 4: RAGAs Evaluation Framework
        =====================================
    """)

    # Resolve dataset path based on role argument
    if role:
        dataset_path = f"data/evaluation/roles/{role}.json"
        run_label = f"role '{role}'"
    else:
        dataset_path = "data/evaluation/test_dataset.json"
        run_label = "all roles"

    # Setup logging
    # NOTE: logging.basicConfig() is a no-op when third-party libraries (transformers,
    # langchain, semantic_router) have already added handlers to the root logger during
    # import. We configure the root logger directly so our FileHandler always attaches.
    log_file = f"data/evaluation/evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    log_format = "%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s"
    formatter = logging.Formatter(log_format)

    # Remove any handlers already attached by imported libraries
    root_logger = logging.getLogger()
    for _h in root_logger.handlers[:]:
        root_logger.removeHandler(_h)
    root_logger.setLevel(logging.DEBUG)

    # Stdout handler
    _stream_handler = logging.StreamHandler(sys.stdout)
    _stream_handler.setFormatter(formatter)
    root_logger.addHandler(_stream_handler)

    # File handler – always writes, regardless of prior basicConfig state
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    _file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    _file_handler.setFormatter(formatter)
    root_logger.addHandler(_file_handler)

    logger = logging.getLogger(__name__)

    # Fine-tune log verbosity per module
    logging.getLogger("src.evaluation.internal_evaluator").setLevel(logging.DEBUG)
    logging.getLogger("src.core.rag_system").setLevel(logging.DEBUG)
    logging.getLogger("src.core.vector_store").setLevel(logging.INFO)

    logger.info("=" * 80)
    logger.info(f"🚀 Starting FinBot RAGAs Evaluation — evaluating {run_label}")
    logger.info(f"📂 Dataset: {dataset_path}")
    logger.info(f"📝 Log file: {log_file}")
    logger.info("=" * 80)

    try:
        logger.info("📊 Checking system readiness...")

        await run_internal_evaluation(dataset_path=dataset_path, role=role)

        logger.info("✅ Evaluation completed successfully!")

        print(f"""
✅ COMPONENT 4 EVALUATION COMPLETE
===================================

📊 Evaluation Scope : {run_label.upper()}
📂 Dataset used     : {dataset_path}
📁 Results saved to : data/evaluation/

📈 Metrics computed:
  • faithfulness
  • answer_relevancy
  • context_precision
  • context_recall
  • answer_correctness

🎯 Ablation configurations run:
  • Full System (RAG + LLM + Guardrails)
  • Direct Vector Search (no LLM)
        """)

    except Exception as e:
        logger.error(f"❌ Evaluation failed: {e}")
        logger.error("Please check the logs for detailed error information")

        print(f"""
❌ EVALUATION ENCOUNTERED ISSUES
==============================

Error: {e}

💡 Troubleshooting Steps:
  1. Ensure Qdrant database is running (localhost:6333)
  2. Check if all collections are properly created
  3. Verify Python environment and dependencies
  4. Check the dataset path exists: {dataset_path}
  5. Review the evaluation logs for specific errors
        """)


if __name__ == "__main__":
    asyncio.run(main())