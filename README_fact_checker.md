The fact-checker persona executes three tasks:
1) **Extract** verifiable claims from text.
2) **Judge** claims by following the procedure:
   1) If a claim is labelled as "political" or "public discourse", verify claim using Google Fact Check Tools.
   2) If labelled as "other" or Google Fact Check returns nothing, use training data to fact-check claim.
   3) If a claim cannot be verified using training data, execute web search.
3) **Generate** a response based on evaluated claims.