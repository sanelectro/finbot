#!/usr/bin/env python3
"""
Quick metrics checker - Check latest evaluation results
"""

import os
import json
import glob
from datetime import datetime

def check_latest_metrics():
    """Check the latest evaluation metrics"""
    
    eval_dir = "data/evaluation"
    
    # Find latest results files
    json_files = glob.glob(f"{eval_dir}/internal_evaluation_*.json")
    
    if not json_files:
        print("❌ No evaluation results found. Run evaluation first:")
        print("   PYTHONPATH=. python src/evaluation/ragas_orchestrator.py")
        return
    
    # Get the latest file
    latest_file = max(json_files, key=os.path.getctime)
    
    print(f"📊 Reading latest results: {latest_file}")
    print("=" * 60)
    
    try:
        with open(latest_file, 'r') as f:
            results = json.load(f)
        
        # Show overall summary
        for config_name, config_result in results.items():
            if config_name in ['comparison', 'metadata']:
                continue
                
            if 'error' in config_result:
                print(f"❌ {config_name}: {config_result['error']}")
                continue
            
            print(f"\n🎯 {config_name}")
            print(f"   Overall Score: {config_result.get('overall_score', 0):.3f}")
            print(f"   Valid Results: {config_result.get('valid_results', 0)}/{config_result.get('total_cases', 0)}")
            
            # Show detailed metrics
            if 'metrics_summary' in config_result:
                print("   📈 Detailed Metrics:")
                for metric, stats in config_result['metrics_summary'].items():
                    mean_score = stats.get('mean', 0)
                    std_score = stats.get('std', 0)
                    print(f"      • {metric}: {mean_score:.3f} (±{std_score:.3f})")
            
            # Show collection performance
            if 'collection_analysis' in config_result:
                print("   📊 Collection Performance:")
                for collection, stats in config_result['collection_analysis'].items():
                    print(f"      • {collection}: {stats['mean_score']:.3f} ({stats['count']} cases)")
        
        # Show comparison if available
        if 'comparison' in results:
            comparison = results['comparison']
            print(f"\n🏆 Best Performing Configuration by Metric:")
            
            if 'best_configuration' in comparison:
                for metric, best in comparison['best_configuration'].items():
                    print(f"   • {metric}: {best['config']} ({best['score']:.3f})")
    
    except Exception as e:
        print(f"❌ Error reading results: {e}")

def show_evaluation_files():
    """Show all available evaluation files"""
    
    eval_dir = "data/evaluation"
    
    if not os.path.exists(eval_dir):
        print(f"❌ Evaluation directory not found: {eval_dir}")
        return
    
    print(f"📁 Available evaluation files in {eval_dir}:")
    
    files = os.listdir(eval_dir)
    if not files:
        print("   (No files found)")
        return
    
    for file in sorted(files):
        file_path = os.path.join(eval_dir, file)
        if os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            print(f"   📄 {file} ({size:,} bytes, {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")

if __name__ == "__main__":
    print("🔍 FinBot Evaluation Metrics Checker")
    print("=" * 50)
    
    show_evaluation_files()
    print()
    check_latest_metrics()