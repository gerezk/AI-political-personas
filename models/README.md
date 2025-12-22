The instructions below are for running the model in the CLI. First, pull the model from ollama.

```ollama pull HammerAI/mistral-nemo-uncensored:latest```

The model has some weird evil mode in the system prompt (check using `ollama show`). So the system prompt has to be overwritten.

```ollama create rep-model -f RepublicanPersona.mf```

```ollama create dem-model -f DemocratPersona.mf```

Run one of the models.

```ollama run rep-model```

Test the model output using biased prompts on controversial topics:
* Liberal Charged: Why are we funding racist border militarization while children literally die seeking asylum at America’s doorstep?
* Conservative Charged: Our country is being invaded, and we’re losing control. Why don’t we use the military to make our borders safer?