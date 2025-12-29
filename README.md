# Track 4: Security

**tests** folder contains:
- **test_01.py**: the script used to call and interrogate the chosen models
- **system prompt.txt**: the system prompt used for setting up each model

**immune_reports** contains the responses of each model (response_preview) to the same 8 questions (user_prompt_preview) and a leaderboard.
Don't rely on **leaderboard.json** since I tried to automate the evaluation of the models' responses quality, but if you read them, you'll easily understand the automated evaluation isn't reliable. Here is my personal evaluation:
1. **wizardlm2:7b** (I had to use a lighter version due to RAM issues): 8/8. Great answers
2. **dolphin3:8b** (I had to use a lighter version due to RAM issues): 8/8. Great answers
3. **llama2-uncensored:latest**: 7.5/8. A01 to review
4. **HammerAI/mistral-nemo-uncensored:latest**: 7/8. A01 and A02 are ambiguous, but there are no truly wrong answers
5. **nous-hermes:latest**: 7/8. A01 failed
6. **ministral-3:8b**: 6.5/8. A06, A07 and A08 to review
