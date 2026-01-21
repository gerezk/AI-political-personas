# Explanation

## Persona Construction

In the folder `modelfiles` you can find all modelfiles, which were used to finetune the democrat and republican llm models.

In order to construct a new llm model use the modelfiles and the following commands:

`ollama create rep-model:your_tag -f YourModelFile.mf`

`ollama create dem-model:your_tag -f YourModelFile.mf`

Or you use the already uploaded models, which can be accessed at the following links:
- [Democrat Model](https://ollama.com/nadinekitzwoegerer/dem-model)
- [Republican Model](https://ollama.com/nadinekitzwoegerer/rep-model)

## Short instructions to upload a finetuned model to the Ollama cloud

1. Rename Model:
If not already done you need to rename your model to also include your username, like this:
`ollama cp your-custom-model ollama-username/your-custom-model`

2. Create a new model on the Ollama registry or use an already existing one.

3. Push Model:
With the command `ollama push ollama-username/your-custom-model` you can send the model to the Ollama registry.

Note you can also use tags to distinguish different model versions. Like `ollama-username/rep-model:latest` or `ollama-username/rep-model:v2`. Of course this tag needs to be added to the model name in step 1.

## Persona Evaluation

For the evaluation we choose to:
1. First generate a set of evaluation prompts: see the file `evaluation_prompts.json`
    Topics include: healthcare, gun regulations, economic policies, tax policies, immigration
2. We then gave both democrat and republican models the prompts and saved their responses in a .jsonl file. See here `eval_results/eval_results_MODELTAG.jsonl`.
    The script for this process is called `evaluation.py`.
3. Then we run a POLITICS model over the models responses, which gives the response a category:
    - LABEL_0: means left
    - LABEL_1: mean neutral
    - LABEL_2: means right
    The script that executes this process is called `politics_evaluation.py`. For more information about the used Politics model see this [webpage](https://huggingface.co/matous-volf/political-leaning-politics).

If you directly want to tun the evaluation for a specific model, just execute the following script: `evaluation_pipeline.py`.

The results of the evaluation will be visualized in the notebook `persona_evaluation.ipynb`.