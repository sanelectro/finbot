# 📊 **FinBot Evaluation Guide**

**Complete guide for running and understanding RAGAs evaluation (Component 4)**

---

## 🚀 **Quick Start for New Developers**

### **Prerequisites Check**
```bash
# 1. Verify system is ready
curl -f http://localhost:6333/collections || echo "❌ Start Qdrant first"

# 2. Check Python environment
python --version  # Should be 3.9+
pip show ragas datasets || echo "❌ Install requirements.txt"
```

### **One-Command Evaluation**
```bash
# Quick verification (no dependencies needed)
python src/evaluation/ragas_health_monitor.py

# Full evaluation (requires system running)
PYTHONPATH=. python src/evaluation/run_ragas_eval.py
```

---

## 📋 **Evaluation Commands Reference**

### **1. Quick Status Check** 🔍
```bash
# Check if evaluation framework is ready
python src/evaluation/ragas_health_monitor.py
```
**Output**: Component status, test dataset info, requirements verification

### **2. Full RAGAs Evaluation** 🧪
```bash
# Complete evaluation with all configurations
PYTHONPATH=. python src/evaluation/run_ragas_eval.py
```
**Output**: Comprehensive metrics across 4 system configurations

### **3. Results Checker** 📊
```bash
# View latest evaluation results
python src/evaluation/check_metrics.py
```
**Output**: Latest scores, collection performance, comparative analysis

### **4. Individual Component Testing** 🔧
```bash
# Test semantic router
PYTHONPATH=. python -c "from src.core.query_router import SemanticQueryRouter; print('✅ Router ready')"

# Test guardrails
PYTHONPATH=. python -c "from src.core.guardrails import GuardrailsOrchestrator; print('✅ Guardrails ready')"

# Test evaluation framework
PYTHONPATH=. python -c "from src.evaluation.internal_evaluator import InternalEvaluator; print('✅ Evaluation ready')"
```

---

## 📁 **Where to Find Results**

### **Real-time Output** 🖥️
**Location**: Terminal/Console during evaluation
```
🎯 Query Classification: 95%+ accuracy
⚡ Routing Speed: < 50ms for query intent classification
📈 Scores: {'faithfulness': 0.782, 'answer_relevancy': 0.856, ...}
✅ Configuration Full System completed in 45.23 seconds
```

### **Detailed Results Files** 📄
**Location**: `data/evaluation/` directory

```bash
# List all evaluation files
ls -la data/evaluation/

# Example output:
drwxr-xr-x  evaluation/
├── 📊 test_dataset.json                      # 45 test cases
├── 📈 internal_evaluation_20260506_143022.json  # Main results
├── 🧪 ragas_evaluation_final_*.json          # RAGAs results
├── 📋 ragas_evaluation_report_*.md           # Formatted report
└── 📝 evaluation_*.log                       # Detailed logs
```

### **JSON Results Structure** 📖
```json
{
  "config_name": "Full System",
  "overall_score": 0.755,
  "total_cases": 45,
  "valid_results": 43,
  "metrics_summary": {
    "faithfulness": {
      "mean": 0.782, "std": 0.124, "min": 0.234, "max": 0.967
    },
    "answer_relevancy": {
      "mean": 0.856, "std": 0.089, "min": 0.567, "max": 0.934
    },
    "context_precision": {
      "mean": 0.734, "std": 0.156, "min": 0.123, "max": 0.945
    },
    "context_recall": {
      "mean": 0.691, "std": 0.198, "min": 0.089, "max": 0.923
    },
    "answer_correctness": {
      "mean": 0.712, "std": 0.143, "min": 0.234, "max": 0.889
    }
  },
  "collection_analysis": {
    "hr": {"count": 6, "mean_score": 0.823},
    "engineering": {"count": 9, "mean_score": 0.756},
    "finance": {"count": 9, "mean_score": 0.689},
    "marketing": {"count": 10, "mean_score": 0.734},
    "general": {"count": 11, "mean_score": 0.798}
  },
  "timestamp": "2026-05-06T14:30:22"
}
}
```

### **Markdown Reports** 📝
**Auto-generated human-readable reports**:

```markdown
# FinBot RAGAs Evaluation Report
Generated: 2026-05-06 14:30:22

## Executive Summary
- **Total Test Cases**: 45
- **Configurations Tested**: 4
- **Evaluation Completed**: 2026-05-06T14:30:22

## Configuration Results
### Full System
**Overall Score**: 0.755
**Valid Results**: 43/45

**Metrics**:
- faithfulness: 0.782
- answer_relevancy: 0.856
- context_precision: 0.734
- context_recall: 0.691
- answer_correctness: 0.712

## Best Performing Configurations
- **faithfulness**: Full System (0.782)
- **answer_relevancy**: Full System (0.856)
```

---

## 🧪 **Understanding the Evaluation**

### **Test Dataset** 📊
**Location**: `data/evaluation/test_dataset.json`

**45 comprehensive test cases** covering:
- **HR** (6 cases): Employee lookups, salary analysis, department data
- **Engineering** (9 cases): Architecture, incident management, API docs
- **Finance** (9 cases): Performance metrics, budget analysis, investments
- **Marketing** (10 cases): Campaigns, analytics, brand strategy
- **General** (11 cases): Policies, onboarding, benefits, procedures

Each test case includes:
```json
{
  "id": 1,
  "question": "What is the name of employee with ID FINEMP1000?",
  "ground_truth": "The employee with ID FINEMP1000 is Mahesh Desai.",
  "collection": "hr",
  "user_role": "hr",
  "category": "employee_lookup",
  "expected_context": "Employee data with ID FINEMP1000"
}
```

### **RAGAs Metrics Explained** 📈

| Metric | Range | What it Measures | Higher = Better |
|--------|-------|------------------|------------------|
| **faithfulness** | 0.0-1.0 | Answer supported by retrieved context | ✅ |
| **answer_relevancy** | 0.0-1.0 | Answer relevance to the question | ✅ |
| **context_precision** | 0.0-1.0 | Usefulness of retrieved contexts | ✅ |
| **context_recall** | 0.0-1.0 | Completeness of context retrieval | ✅ |
| **answer_correctness** | 0.0-1.0 | Answer accuracy vs ground truth | ✅ |

### **Ablation Study Configurations** 🔬

1. **Full System**: All components (semantic router + guardrails + RAG)
2. **No Guardrails**: Semantic router + RAG only
3. **No Semantic Router**: Guardrails + RAG only
4. **Baseline**: Direct vector search only

**Purpose**: Measure the contribution of each component to overall performance

---

## 🔧 **Troubleshooting Evaluation**

### **Common Issues & Solutions** 🚨

#### **1. Import Errors**
```bash
❌ ModuleNotFoundError: No module named 'src.core'

✅ Solution:
export PYTHONPATH=.
# OR prefix commands:
PYTHONPATH=. python src/evaluation/run_ragas_eval.py
```

#### **2. Qdrant Connection Failed**
```bash
❌ Connection refused to localhost:6333

✅ Solutions:
# Check if running
curl http://localhost:6333/collections

# Start Qdrant with Docker
docker run -p 6333:6333 qdrant/qdrant:latest

# OR install locally and start
qdrant
```

#### **3. Missing Dependencies**
```bash
❌ ImportError: No module named 'ragas'

✅ Solution:
pip install -r requirements.txt
# OR individually:
pip install ragas datasets groq
```

#### **4. GROQ API Key Missing**
```bash
❌ GROQ_API_KEY not found

✅ Solution:
# Add to .env file
echo "GROQ_API_KEY=your_key_here" >> .env
# OR export temporarily:
export GROQ_API_KEY="your_key_here"
```

#### **5. No Documents in Collections**
```bash
❌ No search results found

✅ Solution:
# Ingest documents first
python -m src.cli ingest documents --collection hr --recreate
python -m src.cli ingest documents --collection engineering --recreate
```

### **Debug Mode Evaluation** 🐛
```bash
# Run with detailed logging
PYTHONPATH=. python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.evaluation.internal_evaluator import run_internal_evaluation
import asyncio
asyncio.run(run_internal_evaluation())"
```

---

## 📊 **Interpreting Results**

### **Score Ranges** 📈
- **0.8 - 1.0**: Excellent performance
- **0.6 - 0.8**: Good performance  
- **0.4 - 0.6**: Acceptable performance
- **0.0 - 0.4**: Needs improvement

### **Key Performance Indicators** 🎯
- **Overall Score > 0.7**: System is performing well
- **faithfulness > 0.8**: Answers are well-grounded
- **answer_relevancy > 0.8**: Responses are on-topic
- **Collection Balance**: All collections should have similar scores

### **Red Flags** 🚩
- **Overall Score < 0.5**: Major system issues
- **Large std deviation (>0.2)**: Inconsistent performance
- **Collection imbalance**: Some domains underperforming
- **Low valid_results ratio**: System failing frequently

### **Improvement Actions** 🔧
- **Low faithfulness**: Improve context retrieval
- **Low relevancy**: Enhance query understanding
- **Low precision**: Better document filtering
- **Low recall**: Expand search coverage
- **Low correctness**: Improve answer generation

---

## 🎯 **Next Steps After Evaluation**

### **For Developers** 👨‍💻
1. **Analyze Results**: Focus on lowest-scoring metrics
2. **Investigate Issues**: Check logs for specific failures
3. **Optimize Components**: Improve underperforming areas
4. **Re-evaluate**: Run tests after improvements

### **For Stakeholders** 📋
1. **Review Reports**: Check markdown summaries
2. **Compare Configurations**: Understand component value
3. **Performance Trends**: Track improvements over time
4. **Production Readiness**: Validate system quality

### **Continuous Improvement** 🔄
```bash
# Regular evaluation routine
# 1. Make system changes
# 2. Run evaluation
PYTHONPATH=. python src/evaluation/run_ragas_eval.py
# 3. Compare with previous results
python src/evaluation/check_metrics.py
# 4. Iterate based on findings
```

---

## 🏆 **Assignment Verification**

### **Component 4 Checklist** ✅
- [x] **Ground-truth dataset**: 45 test cases (required: 40+)
- [x] **RAGAs metrics**: All 5 implemented (faithfulness, answer_relevancy, context_precision, context_recall, answer_correctness)
- [x] **Ablation study**: 4-configuration comparative analysis
- [x] **Evaluation framework**: Dual system (RAGAs + Internal)

### **Verification Commands** 🔍
```bash
# 1. Verify test dataset
python -c "import json; data=json.load(open('data/evaluation/test_dataset.json')); print(f'✅ {len(data[\"test_cases\"])} test cases')"

# 2. Verify framework
python src/evaluation/ragas_health_monitor.py

# 3. Run sample evaluation
PYTHONPATH=. python src/evaluation/run_ragas_eval.py
```

**🎯 Status: Component 4 COMPLETE & READY FOR DEMONSTRATION**

---

## 📞 **Getting Help**

- **📖 Main Documentation**: `README.md`
- **📊 Project History**: `docs/PROJECT_HISTORY.md`  
- **🎯 Assignment Status**: `ASSIGNMENT_COMPLETION_SUMMARY.md`
- **🔧 API Docs**: `src/api/README.md`
- **❓ Issues**: Check logs in `data/evaluation/evaluation_*.log`

**🚀 Ready to evaluate? Start with:** `python src/evaluation/ragas_health_monitor.py`