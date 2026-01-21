import json
import ollama
from tqdm import tqdm
import os

MODEL_TAG = "v2"

# get the fine tuned LLM models
democrat_model = f'nadinekitzwoegerer/dem-model:{MODEL_TAG}'
republican_model = f'nadinekitzwoegerer/rep-model:{MODEL_TAG}'

EVAL_FOLDER = "eval_results"

# this is the file where the evaluation prompts are stored
EVAL_FILE_PATH = "evaluation_prompts.json"

# this is the file where the prompts + outputs of the finetuned models are stored
EVAL_OUTPUT_PATH = os.path.join(EVAL_FOLDER, f"eval_results_{MODEL_TAG}.jsonl")

# function to load the evaluation prompts
def load_prompts(file_path):
    with open(file_path, 'r') as f:
        prompts = json.load(f)  # Load entire file as one JSON array
    return prompts

def llm_response(
        prompt,
        llm_model
):
    messages = [
        {
            'role': 'user', 
            'content': prompt
        }
    ]

    response = ollama.chat(
        model=llm_model, 
        messages=messages
    )

    return response['message']['content']

def generate_eval_responses(
        eval_prompts_path,
        democrat_model,
        republican_model,
        results_path
):
    # load the evaluation data
    eval_data = load_prompts(eval_prompts_path)

    results = []

    for item in tqdm(eval_data, desc="Evaluating Personas"):
        # response from democrat
        dem_output = llm_response(item['prompt'], llm_model=democrat_model) 

        # response from republican
        rep_output = llm_response(item['prompt'], llm_model=republican_model)

        # store responses
        item['dem_response'] = dem_output
        item['rep_response'] = rep_output

        results.append(item)

    # store in a new jsonl file
    output_file = results_path

    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in results:
            # json.dumps converts the dict to a string
            json_record = json.dumps(entry, ensure_ascii=False)
            f.write(json_record + '\n')
            
    print(f"Evaluation results successfully saved to {output_file}")

if __name__ == "__main__":
    os.makedirs(EVAL_FOLDER, exist_ok=True)
    # load the evaluation data
    eval_data = load_prompts(EVAL_FILE_PATH)

    results = []

    for item in tqdm(eval_data, desc="Evaluating Personas"):
        # response from democrat
        dem_output = llm_response(item['prompt'], llm_model=democrat_model) 

        # response from republican
        rep_output = llm_response(item['prompt'], llm_model=republican_model)

        # store responses
        item['dem_response'] = dem_output
        item['rep_response'] = rep_output

        results.append(item)

    # store in a new jsonl file
    output_file = EVAL_OUTPUT_PATH

    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in results:
            # json.dumps converts the dict to a string
            json_record = json.dumps(entry, ensure_ascii=False)
            f.write(json_record + '\n')
            
    print(f"Evaluation results successfully saved to {output_file}")
