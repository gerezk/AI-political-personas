from ollama import chat, ChatResponse
from typing import Literal, TypedDict
import json
import re
from external_fact_check import google_fact_check

def extract_json(text: str) -> dict:
    # Remove markdown code fences if present
    text = re.sub(r"```(?:json)?", "", text)
    text = text.replace("```", "").strip()

    match = re.search(r"\{[\s\S]*}", text)
    if not match:
        raise ValueError("No JSON object found in model output.")

    return json.loads(match.group())

# Define clear data models
Verdict = Literal["TRUE", "FALSE", "UNVERIFIABLE"]
Party = Literal["REP", "DEM", "UNK"]

class ClaimJudgement(TypedDict):
    Claim: str
    Judgement: Verdict
    Explanation: str

class ModeratorResponse(TypedDict):
    Response: str

class FactChecker:
    def __init__(self, model: str = "fact-checker-model:latest"):
        self.model = model

    def _call_model(self, task_trigger: str, prompt: str) -> dict:
        response: ChatResponse = chat(
            model=self.model,
            messages=[{
                "role": "user",
                "content": f"{task_trigger} {prompt}"
            }]
        )

        return extract_json(response.message.content)

    def extract_claims(self, text: str) -> dict:
        return self._call_model("Extract:", text)

    def judge_claim(self, claim: str) -> dict:
        # Use Google Fact Checker if claim is political
        google_result = google_fact_check(claim)

        # If no return or other type of claim, judge based on training data

        # If training data evaluated to unverifiable, execute web search
        return self._call_model("Judge:", claim)

    def generate_response(self, judgement: ClaimJudgement) -> dict:
        pass # make sure true and unverifiable claims are dropped before feeding to the model since they're not needed

        return self._call_model("Generate:", json.dumps(judgement))

def handle_persona_output(text: str, fact_checker: FactChecker):
    claims = fact_checker.extract_claims(text)

    judgements = []
    for claim in claims:
        judgement = fact_checker.judge_claim(claim["Claim"])
        judgements.append(judgement)

    moderator_responses = []
    for j in judgements:
        response = fact_checker.generate_response(j)
        if response:
            moderator_responses.append(response)

    return {
        "judgements": judgements,
        "moderator_responses": moderator_responses
    }

def main():
    fact_checker = FactChecker()

    political_output = (
        "The Paris Agreement entered into force in 2016, "
        "and it eliminated U.S. fossil fuel production."
    )

    result = handle_persona_output(political_output, fact_checker)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()