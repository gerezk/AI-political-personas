import pandas as pd
import torch
import json
from transformers import pipeline
from tqdm import tqdm
import os

"""
Go to model description: https://huggingface.co/matous-volf/political-leaning-politics

Short explanation of the model from the above webpage:
The model outputs 0 for the left, 1 for the center and 2 for the right leaning. The score of the predicted class is between 13\frac{1}{3}31​ and 1.
"""

POLITICO_MODEL      = "matous-volf/political-leaning-politics"

MODEL_TAG           = "v2"

EVAL_FOLDER         = "eval_results"

EVAL_RESULTS_PATH   = os.path.join(EVAL_FOLDER, f"eval_results_{MODEL_TAG}.jsonl")

CSV_RESULTS_PATH    = os.path.join(EVAL_FOLDER, f"politico_results_{MODEL_TAG}.csv")

def run_evaluation(input_file, output_csv):
    # load the classifier
    # tokenizer 'launch/POLITICS' as recommended by the model author
    classifier = pipeline(
        "text-classification", 
        model=POLITICO_MODEL,
        tokenizer="launch/POLITICS"
    )

    results_for_csv = []

    # load the JSONL responses generated earlier
    with open(input_file, 'r', encoding='utf-8') as f:
        data = [json.loads(line) for line in f]

    for item in tqdm(data, desc="Classifying Responses"):
        prompt = item['prompt']
        
        # evaluate personas
        for persona in ['dem', 'rep']:
            response_text = item[f'{persona}_response']
            
            # Run the classifier
            prediction = classifier(response_text)[0]
            
            # Flatten everything for the CSV/Pandas
            results_for_csv.append({
                'prompt_id': item.get('id'),
                'category': item.get('category'),
                'prompt': prompt,
                'persona_type': "Democrat" if persona == 'dem' else "Republican",
                'llm_response': response_text,
                'predicted_leaning': prediction['label'], # 'left', 'center', or 'right'
                'confidence_score': prediction['score']
            })

    # 3. Create DataFrame and Save to CSV
    df = pd.DataFrame(results_for_csv)
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"Evaluation complete! Saved to {output_csv}")

if __name__ == "__main__":
    run_evaluation(EVAL_RESULTS_PATH, CSV_RESULTS_PATH)