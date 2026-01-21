"""
Analyze fact-checker results for false positives, false negatives, etc.
"""

import json
from pathlib import Path


def analyze_results(json_file: str = "fact_checker_results.json"):
    """Analyze fact-checker results and compute confusion matrix metrics."""

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    results = data['evaluation_results']

    # Initialize counters
    true_positives = []   # FALSE claim correctly detected
    true_negatives = []   # TRUE claim correctly passed
    false_positives = []  # TRUE claim incorrectly flagged as false
    false_negatives = []  # FALSE claim missed (not detected)

    for r in results:
        expected = r['expected']
        correct = r['correct']

        if expected == "FALSE" and correct:
            true_positives.append(r)
        elif expected == "TRUE" and correct:
            true_negatives.append(r)
        elif expected == "TRUE" and not correct:
            false_positives.append(r)
        elif expected == "FALSE" and not correct:
            false_negatives.append(r)

    # Calculate metrics
    tp = len(true_positives)
    tn = len(true_negatives)
    fp = len(false_positives)
    fn = len(false_negatives)

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total * 100 if total > 0 else 0
    precision = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    # Print summary
    print("=" * 70)
    print("FACT-CHECKER CONFUSION MATRIX ANALYSIS")
    print("=" * 70)
    print(f"\nTotal claims evaluated: {total}")
    print(f"  - TRUE claims: {tn + fp}")
    print(f"  - FALSE claims: {tp + fn}")

    print("\n" + "-" * 70)
    print("CONFUSION MATRIX")
    print("-" * 70)
    print(f"                    Predicted Positive    Predicted Negative")
    print(f"  Actual FALSE      TP = {tp:3d}              FN = {fn:3d}")
    print(f"  Actual TRUE       FP = {fp:3d}              TN = {tn:3d}")

    print("\n" + "-" * 70)
    print("METRICS")
    print("-" * 70)
    print(f"  Accuracy:   {accuracy:.2f}%  ({tp + tn}/{total})")
    print(f"  Precision:  {precision:.2f}%  (TP / (TP + FP) = {tp} / {tp + fp})")
    print(f"  Recall:     {recall:.2f}%  (TP / (TP + FN) = {tp} / {tp + fn})")
    print(f"  F1 Score:   {f1:.2f}%")

    # Print false positives details
    if false_positives:
        print("\n" + "=" * 70)
        print(f"FALSE POSITIVES ({fp}) - TRUE claims incorrectly flagged")
        print("=" * 70)
        for r in false_positives:
            print(f"\n[{r['claim_number']}] {r['party']}: {r['claim']}")
            print(f"    Response: {r['response'][:150]}...")

    # Print false negatives details
    if false_negatives:
        print("\n" + "=" * 70)
        print(f"FALSE NEGATIVES ({fn}) - FALSE claims NOT detected")
        print("=" * 70)
        for r in false_negatives:
            print(f"\n[{r['claim_number']}] {r['party']}: {r['claim']}")
            print(f"    Response: {r['response'][:150]}...")

    # Party-wise analysis
    print("\n" + "=" * 70)
    print("PARTY-WISE ANALYSIS")
    print("=" * 70)

    for party in ["DEM", "REP"]:
        party_results = [r for r in results if r['party'] == party]
        party_fp = [r for r in false_positives if r['party'] == party]
        party_fn = [r for r in false_negatives if r['party'] == party]
        party_tp = [r for r in true_positives if r['party'] == party]
        party_tn = [r for r in true_negatives if r['party'] == party]

        p_total = len(party_results)
        p_correct = len(party_tp) + len(party_tn)
        p_accuracy = p_correct / p_total * 100 if p_total > 0 else 0

        print(f"\n{party}:")
        print(f"  Total: {p_total}, Correct: {p_correct}, Accuracy: {p_accuracy:.2f}%")
        print(f"  TP: {len(party_tp)}, TN: {len(party_tn)}, FP: {len(party_fp)}, FN: {len(party_fn)}")

    print("\n" + "=" * 70)

    return {
        'true_positives': tp,
        'true_negatives': tn,
        'false_positives': fp,
        'false_negatives': fn,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }


if __name__ == "__main__":
    analyze_results()
