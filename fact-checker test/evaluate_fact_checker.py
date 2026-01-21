"""
Fact-Checker Model Evaluation Script
Uses HammerAI/mistral-nemo-uncensored:latest with fact-checker.mf system prompt
Evaluates performance on claims.txt
"""

import ollama
import time
from pathlib import Path
from typing import Dict, List, Tuple
import json
import re


class FactCheckerEvaluator:
    """Evaluates a fact-checker model using claims from a file."""
    
    def __init__(self, model_name: str = "fact-checker", modelfile_path: str = "model_files/fact-checker.mf"):
        """
        Initialize the evaluator.
        
        Args:
            model_name: Name to give the created model
            modelfile_path: Path to the modelfile with system prompt
        """
        self.model_name = model_name
        self.modelfile_path = Path(modelfile_path)
        self.results = []
        
    def parse_modelfile(self) -> dict:
        """Parse a Modelfile and extract its components."""
        with open(self.modelfile_path, 'r', encoding='utf-8') as f:
            content = f.read()

        result = {'parameters': {}}

        # Extract FROM
        from_match = re.search(r'^FROM\s+(.+)$', content, re.MULTILINE)
        if from_match:
            result['from_'] = from_match.group(1).strip()

        # Extract SYSTEM (handles multi-line with triple quotes)
        system_match = re.search(r'SYSTEM\s+"""(.*?)"""', content, re.DOTALL)
        if system_match:
            result['system'] = system_match.group(1).strip()

        # Extract PARAMETERs
        for param_match in re.finditer(r'^PARAMETER\s+(\w+)\s+(.+)$', content, re.MULTILINE):
            key = param_match.group(1)
            value = param_match.group(2).strip()
            # Try to convert to appropriate type
            try:
                value = float(value)
            except ValueError:
                pass
            result['parameters'][key] = value

        return result

    def create_model(self):
        """Create the fact-checker model from the modelfile."""
        print(f"Creating model '{self.model_name}' from {self.modelfile_path}...")

        try:
            # Parse the modelfile
            config = self.parse_modelfile()

            # Create the model using ollama
            ollama.create(
                model=self.model_name,
                from_=config.get('from_'),
                system=config.get('system'),
                parameters=config.get('parameters') or None
            )
            print(f"✓ Model '{self.model_name}' created successfully")

        except Exception as e:
            print(f"✗ Error creating model: {e}")
            raise
    
    def parse_claims_file(self, claims_file: str) -> List[Dict]:
        """
        Parse the claims.txt file.
        
        Args:
            claims_file: Path to claims file
            
        Returns:
            List of claim dictionaries with party, expected_result, and text
        """
        claims = []
        
        with open(claims_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Parse format: [PARTY][TRUE/FALSE] claim text
                match = re.match(r'\[([A-Z]+)\]\[([A-Z]+)\]\s+(.+)', line)
                if match:
                    party, expected, claim_text = match.groups()
                    claims.append({
                        'party': party,
                        'expected': expected,
                        'text': claim_text
                    })
        
        return claims
    
    def check_claim(self, claim_text: str) -> Tuple[str, float]:
        """
        Send a claim to the fact-checker model and get response.
        
        Args:
            claim_text: The claim to fact-check
            
        Returns:
            Tuple of (response_text, response_time)
        """
        start_time = time.time()
        
        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': claim_text
                    }
                ]
            )
            
            response_time = time.time() - start_time
            response_text = response['message']['content'].strip()
            
            return response_text, response_time
            
        except Exception as e:
            print(f"Error checking claim: {e}")
            return f"ERROR: {e}", time.time() - start_time
    
    def evaluate_response(self, response: str, expected: str) -> Dict:
        """
        Evaluate if the model's response is correct.
        
        Args:
            response: Model's response text
            expected: Expected result (TRUE or FALSE)
            
        Returns:
            Dictionary with evaluation results
        """
        response_lower = response.lower()
        
        # Check for special responses
        no_false_claims = "no false claims" in response_lower
        no_verifiable_claims = "no verifiable claims" in response_lower
        
        if expected == "TRUE":
            # For true claims, we expect "No false claims in the text"
            correct = no_false_claims
            classification = "correct" if correct else "incorrect"
        else:  # expected == "FALSE"
            # For false claims, we expect a fact-check response (not the special messages)
            correct = not no_false_claims and not no_verifiable_claims and len(response) > 20
            classification = "correct" if correct else "incorrect"
        
        return {
            'correct': correct,
            'classification': classification,
            'no_false_claims_detected': no_false_claims,
            'no_verifiable_claims_detected': no_verifiable_claims
        }
    
    def evaluate_all_claims(self, claims_file: str = "claims.txt") -> Dict:
        """
        Evaluate all claims in the file.
        
        Args:
            claims_file: Path to claims file
            
        Returns:
            Dictionary with evaluation statistics
        """
        print(f"\nEvaluating claims from {claims_file}...")
        claims = self.parse_claims_file(claims_file)
        print(f"Found {len(claims)} claims to evaluate\n")
        
        correct_count = 0
        total_time = 0
        
        for idx, claim in enumerate(claims, 1):
            print(f"[{idx}/{len(claims)}] Evaluating: {claim['text'][:60]}...")
            
            response, response_time = self.check_claim(claim['text'])
            evaluation = self.evaluate_response(response, claim['expected'])
            
            # Store result
            result = {
                'claim_number': idx,
                'party': claim['party'],
                'claim': claim['text'],
                'expected': claim['expected'],
                'response': response,
                'response_time': response_time,
                **evaluation
            }
            self.results.append(result)
            
            if evaluation['correct']:
                correct_count += 1
                status = "✓ CORRECT"
            else:
                status = "✗ INCORRECT"
            
            print(f"  {status} (Expected: {claim['expected']}, Time: {response_time:.2f}s)")
            print(f"  Response: {response[:100]}{'...' if len(response) > 100 else ''}\n")
            
            total_time += response_time
        
        # Calculate statistics
        accuracy = (correct_count / len(claims)) * 100 if claims else 0
        avg_time = total_time / len(claims) if claims else 0
        
        # Party-wise statistics
        dem_results = [r for r in self.results if r['party'] == 'DEM']
        rep_results = [r for r in self.results if r['party'] == 'REP']
        
        dem_accuracy = (sum(1 for r in dem_results if r['correct']) / len(dem_results) * 100) if dem_results else 0
        rep_accuracy = (sum(1 for r in rep_results if r['correct']) / len(rep_results) * 100) if rep_results else 0
        
        # True/False claim statistics
        true_claims = [r for r in self.results if r['expected'] == 'TRUE']
        false_claims = [r for r in self.results if r['expected'] == 'FALSE']
        
        true_accuracy = (sum(1 for r in true_claims if r['correct']) / len(true_claims) * 100) if true_claims else 0
        false_accuracy = (sum(1 for r in false_claims if r['correct']) / len(false_claims) * 100) if false_claims else 0
        
        stats = {
            'total_claims': len(claims),
            'correct': correct_count,
            'incorrect': len(claims) - correct_count,
            'overall_accuracy': accuracy,
            'average_response_time': avg_time,
            'total_time': total_time,
            'dem_accuracy': dem_accuracy,
            'rep_accuracy': rep_accuracy,
            'true_claim_accuracy': true_accuracy,
            'false_claim_accuracy': false_accuracy,
            'dem_claims': len(dem_results),
            'rep_claims': len(rep_results),
            'true_claims_count': len(true_claims),
            'false_claims_count': len(false_claims)
        }
        
        return stats
    
    def print_summary(self, stats: Dict):
        """Print evaluation summary."""
        print("\n" + "="*70)
        print("FACT-CHECKER EVALUATION SUMMARY")
        print("="*70)
        print(f"Model: {self.model_name}")
        print(f"Base Model: HammerAI/mistral-nemo-uncensored:latest")
        print(f"System Prompt: {self.modelfile_path}")
        print("-"*70)
        print(f"Total Claims Evaluated: {stats['total_claims']}")
        print(f"Correct: {stats['correct']}")
        print(f"Incorrect: {stats['incorrect']}")
        print(f"Overall Accuracy: {stats['overall_accuracy']:.2f}%")
        print("-"*70)
        print(f"DEM Claims: {stats['dem_claims']} (Accuracy: {stats['dem_accuracy']:.2f}%)")
        print(f"REP Claims: {stats['rep_claims']} (Accuracy: {stats['rep_accuracy']:.2f}%)")
        print("-"*70)
        print(f"TRUE Claims: {stats['true_claims_count']} (Accuracy: {stats['true_claim_accuracy']:.2f}%)")
        print(f"FALSE Claims: {stats['false_claims_count']} (Accuracy: {stats['false_claim_accuracy']:.2f}%)")
        print("-"*70)
        print(f"Average Response Time: {stats['average_response_time']:.2f}s")
        print(f"Total Evaluation Time: {stats['total_time']:.2f}s ({stats['total_time']/60:.2f} minutes)")
        print("="*70 + "\n")
    
    def save_results(self, output_file: str = "fact_checker_results.json"):
        """Save detailed results to JSON file."""
        results_data = {
            'model_info': {
                'model_name': self.model_name,
                'base_model': 'HammerAI/mistral-nemo-uncensored:latest',
                'modelfile': str(self.modelfile_path)
            },
            'evaluation_results': self.results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Detailed results saved to {output_file}")


def main():
    """Main evaluation function."""
    # Initialize evaluator
    evaluator = FactCheckerEvaluator(
        model_name="fact-checker",
        modelfile_path="fact-checker.mf"
    )
    
    # Create the model
    evaluator.create_model()
    
    # Evaluate all claims
    stats = evaluator.evaluate_all_claims("claims.txt")
    
    # Print summary
    evaluator.print_summary(stats)
    
    # Save results
    evaluator.save_results("fact_checker_results.json")


if __name__ == "__main__":
    main()
