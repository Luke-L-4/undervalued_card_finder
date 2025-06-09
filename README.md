# undervalued_card_finder
- Project to identify undervalued basketball cards using Python. This project integrates APIs, data cleaning, database querying, and modeling


## Search Strategy
- This app is designed to search eBay using highly specific criteria — including player name, card set, and card condition — to ensure that the pricing data collected is consistent and comparable
- For example, instead of broadly searching for "Luka Doncic Rookie Card" (which would return listings across many sets and conditions), the app might target "Luka Doncic Prizm Rookie Card PSA 10" to isolate only identical cards. This level of specificity helps maintain data integrity and allows for more accurate price comparisons across listings

## Notes
- The eBay Production API has a rate limit of **5,000 calls per day** for analytics endpoints.
- Consider batching or scheduling requests to stay within this limit.