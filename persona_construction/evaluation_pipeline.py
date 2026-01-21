from evaluation import *
from politics_evalution import *
import os

# specify which model you want to evaluate
MODEL_TAG           = "v3.2"

EVAL_FOLDER         = "eval_results"

# this is the file where the evaluation prompts are stored
PROMPTS_PATH        = "evaluation_prompts.json"

# this is the file where the llm responses for the evaluation prompts are stored
EVAL_OUTPUT_PATH    = os.path.join(EVAL_FOLDER, f"eval_results_{MODEL_TAG}.jsonl")

# this is the csv file that contains the political leaning of the models
CSV_RESULTS_PATH    = os.path.join(EVAL_FOLDER, f'politico_results_{MODEL_TAG}.csv')


if __name__ == "__main__":
    os.makedirs(EVAL_FOLDER, exist_ok=True)
    print("Generating LLM responses")
    generate_eval_responses(
        eval_prompts_path = PROMPTS_PATH,
        democrat_model = f"nadinekitzwoegerer/dem-model:{MODEL_TAG}",
        republican_model = f"nadinekitzwoegerer/rep-model:{MODEL_TAG}",
        results_path = EVAL_OUTPUT_PATH
    )

    print("Running Evaluation with POLITICO model.")
    run_evaluation(EVAL_OUTPUT_PATH, CSV_RESULTS_PATH)