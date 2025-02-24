BRAND_ENCODING = {
        'HDRUK': 3,
        'SAIL': 2,
        'ADP': 1,
        'healthdatagateway': 3
}

BRAND_LOGO_PATHS = {
    0: {'path': 'images/concept_library_logo.png', 'href': '/' },
    1: {'path': 'images/adp_logo.png', 'href': '/ADP' },
    2: {'path': 'images/sail_logo.png', 'href': '/SAIL' },
    3: {'path': 'images/hdruk_logo.png', 'href': '/HDRUK' }
}

BRAND_LABELS = [
                    {'label': 'HDR UK', 'value': 3},
                    {'label': 'SAIL', 'value': 2},
                    {'label': 'ADP', 'value': 1},
                    {'label': 'Concept Library', 'value': 0}
                ]

USER_TYPE_LABELS = [
                    {'label': 'Authenticated', 'value': 1},
                    {'label': 'Non-Authenticated', 'value': 0}
              ]

# granularity options for the time series chart
GRANULARITY_OPTIONS  = [
                            {"label": "Monthly", "value": 1},
                            {"label": "Quaterly", "value": 2},
                            {"label": "Yearly", "value": 3}
                    ]

# Define the granularity settings as a dictionary
GRANULARITY_SETTINGS = {
    1: {'freq': 'M', 'date_format': "%b %Y"},  # Monthly: Format as "Jun 2023"
    2: {'freq': 'Q', 'date_format': "Q%q %Y"},  # Quarterly: Format as "Q1 2023"
    3: {'freq': 'Y', 'date_format': "%Y"},     # Yearly: Format as "2023"
}

