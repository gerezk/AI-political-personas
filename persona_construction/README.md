# Quick Explanation

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

# Short Model Version Explanation

For a detailed explanation see the Final Project Report.

## Version 1.0: 
This Modelfile creates two ideologically rigid personas: a Staunch Democrat and a Modern Republican governed by specific tables of non-negotiable core beliefs and allowed justifications. Each persona utilizes a unique rhetorical toolkit, such as "Aggressive Pragmatism" for the Democrat or "Common Sense Populism" for the Republican, to frame policy through specific linguistic rhythms and vocabularies. The model is strictly constrained to maintain ideological consistency, prioritizing its programmed political framework over user influence within a 150 word response limit.

### Problem for Version 1.0:
- Even though we prompted the model to keep its answer short, it outputed very long paragraphs, well above 150 words.

## Version 2.0:
We added the parameter `PARAMETER num_predict 150` to strictly force the model to stay under 150 tokens. And added a sentence right at the end of the System Prompt, that again says the model to create a response under 150 words, additionally to the sentence in the middle of the System Prompt.

This solved the problem of very long responses, the models now restricted themselves to shorter more consise responses.

## Version 3.0:
Modelfiles were restructured to be more instruction heavy and structured. A **Rhetorical Spine** with a list like structure was added, to ensure every response follows a consistent flow. The democrat persona was refined from a general "congressional leader" to a more specific "senior leader/patriot", the republican persona moved from an RFK Jr. medical skeptic persona to a more broader "conservative populist" protecting faith, family and freedom.
Also explicit Persuasion mechanics were added, such as anaphora, rhetorical questions and villian framing.

### Version 3.1:
The parameter `PARAMETER num_predict 150` was added again and the model was given a sentence at the end to strictly force itself to stay under 150 words for its response.

### Problems for Version 3.0 and 3.1:
The model now outputed answers in a list like structure and used the format of the Rhetorical Spine as exact sentence format. 
Example output: 
> Human Impact First: ...
Systemic Diagnosis: ...
Democratic Solution: ..
Moral Contrast: ..
Contrast Close: ...

## Version 3.2:
Explicit sentences such as: 
> Use this as a guideline for your response. DO NOT CREATE A LIST AS YOUR RESONSE.

were added.
Critical Formatting Rules were added and a sentence at the end to not answer in a list like structure, such as:

> Write in natural, flowing paragraphs - no lists, no bullets, no labeled sections.

## Problems for Version 3.2:
The above changes to the System prompt, unfortunately did not solve the error of the list like responses. This was due to the problem that many uncensored models tend to mimic the structure of the prompt they are given.

## Final Model Version 3.3
To improve instruction following we removed the multi-level numbered lists like ` 1) , 2) , 3)` and descriptive step-labels `"Human Impact First -"`. We standardized all secondary guidelines into a flat Markdown bullet structure (-) ensuring the model treats all constraints with equal weight and reducing formatting-induced confusion.
Furthermore we extended the max token parameter to 300 tokens `PARAMETER num_predict 300`, since in some cases the model got interrupted mid sentence.
