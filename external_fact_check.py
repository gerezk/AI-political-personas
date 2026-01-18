import requests
from ollama import chat, web_fetch, web_search

GOOGLE_API_KEY = "AIzaSyC1j8sSB1TNnX8ZNj0qH-1mJ6iZXmJf28k"
GOOGLE_BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

OLLAMA_API_KEY = "0c6853c3cac8464c9b0cb1c8be6e7a02.TEC9AciWHS2S6Lc6t1kfZ6ij"
OLLAMA_BASE_URL = "https://ollama.com/api/web_search"


def google_fact_check(claim, language="en-US", page_size=5):
    params = {
        "query": claim,
        "languageCode": language,
        "pageSize": page_size,
        "key": GOOGLE_API_KEY
    }

    response = requests.get(GOOGLE_BASE_URL, params=params, timeout=10)
    response.raise_for_status()

    return response.json()

def execute_web_search():
    assert False, "Not implemented"

# if __name__ == "__main__":
#     claim = "The Inflation Reduction Act raised taxes on the middle class"
#
#     result = fact_check_search(claim)
#
#     if "claims" not in result:
#         print("No fact checks found.")
#     else:
#         for item in result["claims"]:
#             text = item.get("text")
#             claimant = item.get("claimant")
#             reviews = item.get("claimReview", [])
#
#             print(f"\nClaim: {text}")
#             if claimant:
#                 print(f"Claimant: {claimant}")
#
#             for review in reviews:
#                 print(f"  Publisher: {review.get('publisher', {}).get('name')}")
#                 print(f"  Rating: {review.get('textualRating')}")
#                 print(f"  URL: {review.get('url')}")