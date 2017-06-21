# ga-gtm-validator
Validates GA Custom Dimensions and GTM tags across a given set of GA properties and containers

# Init

Create file **fetch_source.py** with the following structure defined within:
```
properties = {
    'property_name': {
        'gaAccountId': '123456',
        'gaPropertyId': 'UA-123456-1',
        'gaProfileId': 'ga:123456',
        'gtmAccountId': '123456',
        'gtmContainerId': '123456'
    },
    'second_property_name': {
        'gaAccountId': '234567',
        'gaPropertyId': 'UA-234567-1',
        'gaProfileId': 'ga:234567',
        'gtmAccountId': '234567',
        'gtmContainerId': '234567'
    }
}
```

# Run

Run with `python fetch.py`.

# What happens

First, the script creates a file **dimensions.csv** where each property is scanned for Custom Dimension names (dimensions 1-200).

Then the GA reporting API is queried for total number of hits over last 7 days that each active Custom Dimension has received.

Next, published versions of the given GTM containers are fetched, with each Universal Analytics tag added to a new CSV for the given property. This CSV contains, again, each Custom Dimension (from 1-200) with the variable name or value that the Custom Dimension has been setup with in the tag.
