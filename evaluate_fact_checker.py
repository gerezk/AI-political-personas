# -*- coding: utf-8 -*-
"""
Evaluate the fact-checker model (group5/fact-checker-mistral:v1) on claims.txt
Compares model predictions against ground truth labels.
"""

import ollama
import json
import re
from typing import List, Tuple, Dict
from tqdm import tqdm
from collections import defaultdict

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

def print_colored(text: str, color: str, bold: bool = False):
    """Print text with color."""
    prefix = Colors.BOLD if bold else ''
    print(f"{prefix}{color}{text}{Colors.RESET}")

def parse_claims_file(filepath: str) -> List[Tuple[str, str, str]]:
    """
    Parse claims.txt file.
    Returns list of tuples: (origin, expected_verdict, claim_text)
    Format: [ORIGIN][EXPECTED_VERDICT] claim text
    """
    claims = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            # Parse: [DEM][TRUE] text or [REP][FALSE] text
            match = re.match(r'\[(\w+)\]\[(\w+)\]\s+(.*)', line)
            if match:
                origin = match.group(1)
                expected_verdict = match.group(2)
                claim_text = match.group(3)
                claims.append((origin, expected_verdict, claim_text))
    
    return claims

def fact_check_claim(model: str, claim: str) -> Dict:
    """
    Send a single claim to the fact-checker model for evaluation.
    Returns the parsed JSON response with verdict and reasoning.
    """
    prompt = f"""FACTCHECK_CLAIM
Claim: {claim}

Evaluate this factual claim. Return JSON with:
{{
  "claim_text": "...",
  "verdict": "CORRECT|INCORRECT|UNVERIFIABLE_WITHOUT_SOURCES",
  "why_short": "..."
}}
"""
    
    try:
        response = ollama.chat(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            format='json'
        )
        
        result = json.loads(response['message']['content'])
        return result
    except json.JSONDecodeError:
        return {
            'claim_text': claim,
            'verdict': 'ERROR',
            'why_short': 'Failed to parse model response as JSON'
        }
    except Exception as e:
        return {
            'claim_text': claim,
            'verdict': 'ERROR',
            'why_short': str(e)
        }

def map_verdict(model_verdict: str) -> str:
    """
    Map model verdict to expected verdict format.
    Model returns: CORRECT, INCORRECT, UNVERIFIABLE_WITHOUT_SOURCES, ERROR
    Ground truth: TRUE, FALSE
    """
    verdict_map = {
        'CORRECT': 'TRUE',
        'INCORRECT': 'FALSE',
        'UNVERIFIABLE_WITHOUT_SOURCES': 'UNVERIFIABLE',
        'ERROR': 'ERROR'
    }
    return verdict_map.get(model_verdict, 'UNKNOWN')

def evaluate_model(claims_file: str, model: str) -> Dict:
    """
    Evaluate the fact-checker model on all claims.
    Returns evaluation metrics.
    """
    
    # Parse claims
    claims = parse_claims_file(claims_file)
    print_colored(f"\nLoaded {len(claims)} claims from {claims_file}\n", Colors.CYAN, bold=True)
    
    # Track results
    results = []
    stats = {
        'total': len(claims),
        'correct': 0,
        'incorrect': 0,
        'unverifiable': 0,
        'error': 0,
        'by_origin': defaultdict(lambda: {'correct': 0, 'total': 0}),
        'by_expected': defaultdict(lambda: {'correct': 0, 'total': 0})
    }
    
    # Evaluate each claim
    pbar = tqdm(total=len(claims), desc="Evaluating claims", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
    
    for origin, expected_verdict, claim_text in claims:
        # Get model prediction
        model_result = fact_check_claim(model, claim_text)
        model_verdict = model_result.get('verdict', 'ERROR')
        mapped_verdict = map_verdict(model_verdict)
        
        # Check if prediction matches expected
        is_correct = (expected_verdict == 'TRUE' and model_verdict == 'CORRECT') or \
                     (expected_verdict == 'FALSE' and model_verdict == 'INCORRECT')
        
        # Store result
        results.append({
            'claim': claim_text,
            'origin': origin,
            'expected': expected_verdict,
            'predicted': model_verdict,
            'mapped': mapped_verdict,
            'correct': is_correct,
            'reasoning': model_result.get('why_short', '')
        })
        
        # Update stats
        stats['by_origin'][origin]['total'] += 1
        stats['by_expected'][expected_verdict]['total'] += 1
        
        if is_correct:
            stats['correct'] += 1
            stats['by_origin'][origin]['correct'] += 1
            stats['by_expected'][expected_verdict]['correct'] += 1
        
        if model_verdict == 'UNVERIFIABLE_WITHOUT_SOURCES':
            stats['unverifiable'] += 1
        elif model_verdict == 'ERROR':
            stats['error'] += 1
        elif not is_correct:
            stats['incorrect'] += 1
        
        pbar.update(1)
    
    pbar.close()
    
    return {
        'results': results,
        'stats': stats
    }

def print_evaluation_report(evaluation: Dict):
    """Print a comprehensive evaluation report."""
    
    results = evaluation['results']
    stats = evaluation['stats']
    
    # Overall metrics
    accuracy = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
    
    print_colored("\n" + "="*70, Colors.BOLD)
    print_colored("EVALUATION REPORT: Fact-Checker Model", Colors.BOLD, bold=True)
    print_colored("="*70, Colors.BOLD)
    
    print_colored(f"\nOverall Accuracy: {accuracy:.2%} ({stats['correct']}/{stats['total']})", Colors.CYAN, bold=True)
    print_colored(f"  ✓ Correct: {stats['correct']}", Colors.GREEN)
    print_colored(f"  ✗ Incorrect: {stats['incorrect']}", Colors.RED)
    print_colored(f"  ? Unverifiable: {stats['unverifiable']}", Colors.YELLOW)
    print_colored(f"  ⚠ Errors: {stats['error']}", Colors.RED)
    
    # By origin
    print_colored("\nBy Origin:", Colors.CYAN, bold=True)
    for origin in sorted(stats['by_origin'].keys()):
        data = stats['by_origin'][origin]
        origin_acc = data['correct'] / data['total'] if data['total'] > 0 else 0
        print_colored(f"  {origin}: {origin_acc:.2%} ({data['correct']}/{data['total']})", Colors.CYAN)
    
    # By expected verdict
    print_colored("\nBy Expected Verdict:", Colors.CYAN, bold=True)
    for verdict in sorted(stats['by_expected'].keys()):
        data = stats['by_expected'][verdict]
        verdict_acc = data['correct'] / data['total'] if data['total'] > 0 else 0
        print_colored(f"  {verdict}: {verdict_acc:.2%} ({data['correct']}/{data['total']})", Colors.CYAN)
    
    # Show some incorrect predictions
    incorrect = [r for r in results if not r['correct']]
    if incorrect:
        print_colored(f"\n{'─'*70}", Colors.YELLOW)
        print_colored(f"Incorrect Predictions ({len(incorrect)} total):", Colors.YELLOW, bold=True)
        print_colored(f"{'─'*70}", Colors.YELLOW)
        
        for i, r in enumerate(incorrect[:10]):  # Show first 10
            print_colored(f"\n[{i+1}] {r['origin']} | Expected: {r['expected']} | Got: {r['predicted']}", Colors.RED, bold=True)
            print_colored(f"Claim: {r['claim']}", Colors.YELLOW)
            print_colored(f"Reason: {r['reasoning']}", Colors.YELLOW)
        
        if len(incorrect) > 10:
            print_colored(f"\n... and {len(incorrect) - 10} more", Colors.YELLOW)
    
    print_colored("\n" + "="*70 + "\n", Colors.BOLD)

def save_results_json(evaluation: Dict, output_file: str = 'evaluation_results.json'):
    """Save detailed results to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evaluation, f, indent=2, ensure_ascii=False)
    print_colored(f"Results saved to {output_file}", Colors.GREEN)

if __name__ == '__main__':
    FACTCHECK_MODEL = 'group5/fact-checker-mistral:v1'
    CLAIMS_FILE = 'claims.txt'
    
    print_colored(f"\nStarting evaluation with model: {FACTCHECK_MODEL}", Colors.CYAN, bold=True)
    print_colored(f"Claims file: {CLAIMS_FILE}\n", Colors.CYAN)
    
    # Run evaluation
    evaluation = evaluate_model(CLAIMS_FILE, FACTCHECK_MODEL)
    
    # Print report
    print_evaluation_report(evaluation)
    
    # Save results
    save_results_json(evaluation)