# undervalued_card_finder
- Project to identify undervalued basketball cards using Python. This project integrates APIs, data cleaning, database querying, and modeling


## Search Strategy
- This app will search by player name, card set, and condition so that card pricing data may be accurately compared
- For example: This app will be used to search for "Luke Doncic Prizm Rookie Card PSA 10" so that card prices are being compared across identical card types and conditions rather than simply searching for "Luka Doncic Rookie Card"
as the card set and condition will vary in a way that prevents true consistency of data

## Notes
- The eBay Production API has a rate limit of **5,000 calls per day** for analytics endpoints.
- Consider batching or scheduling requests to stay within this limit.