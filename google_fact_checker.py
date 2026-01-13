import requests
import os

API_KEY = 'AIzaSyC1j8sSB1TNnX8ZNj0qH-1mJ6iZXmJf28k'
BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def fact_check_search(claim, language="en-US", page_size=5):
    params = {
        "query": claim,
        "languageCode": language,
        "pageSize": page_size,
        "key": API_KEY
    }

    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()

    return response.json()

if __name__ == "__main__":
    claim = "The Inflation Reduction Act raised taxes on the middle class"

    result = fact_check_search(claim)

    if "claims" not in result:
        print("No fact checks found.")
    else:
        for item in result["claims"]:
            text = item.get("text")
            claimant = item.get("claimant")
            reviews = item.get("claimReview", [])

            print(f"\nClaim: {text}")
            if claimant:
                print(f"Claimant: {claimant}")

            for review in reviews:
                print(f"  Publisher: {review.get('publisher', {}).get('name')}")
                print(f"  Rating: {review.get('textualRating')}")
                print(f"  URL: {review.get('url')}")