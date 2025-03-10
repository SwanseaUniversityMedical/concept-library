# Maps brand names to numeric encoding values
BRAND_ENCODING = {
        'HDRUK': 3,
        'SAIL': 2,
        'ADP': 1,
        'healthdatagateway': 3
}
# Associates brand encoding values with logo file paths and their respective URLs
BRAND_LOGO_PATHS = {
    0: {'path': 'images/concept_library_logo.png', 'href': '/' },
    1: {'path': 'images/adp_logo.png', 'href': '/ADP' },
    2: {'path': 'images/sail_logo.png', 'href': '/SAIL' },
    3: {'path': 'images/hdruk_logo.png', 'href': '/HDRUK' }
}
# List of brand names with their corresponding encoding values
BRAND_LABELS = [
                    {'label': 'HDR UK', 'value': 3},
                    {'label': 'SAIL', 'value': 2},
                    {'label': 'ADP', 'value': 1},
                    {'label': 'Concept Library', 'value': 0}
                ]
# Defines the types of users (Authenticated and Non-Authenticated) with corresponding values
USER_TYPE_LABELS = [
                    {'label': 'Authenticated', 'value': 1},
                    {'label': 'Non-Authenticated', 'value': 0}
              ]

# Options for the granularity of time series data (Monthly, Quarterly, Yearly)
GRANULARITY_OPTIONS  = [
                            {"label": "Monthly", "value": 1 },
                            {"label": "Quarterly", "value": 2},
                            {"label": "Yearly", "value": 3}
                    ]

# Define the granularity settings as a dictionary
GRANULARITY_SETTINGS = {
    1: {'freq': 'MS', 'date_format': "%b %Y", "dtick":"M4", "axis_label": "Month"},  # Monthly: Format as "Jun 2023"
    2: {'freq': 'QS', 'date_format': "Q%q %Y", "dtick":"M3", "axis_label": "Quarter"},  # Quarterly: Format as "Q1 2023"
    3: {'freq': 'YS', 'date_format': "%Y", "dtick":"M12", "axis_label": "Year"},     # Yearly: Format as "2023"
}

# Phenotype Dataframe Columns
PHENOTYPE_COLUMNS_SELECT = ['history_date', 'id', 'brands', 'publish_status', 'history_id']
# Requests Dataframe Columns
REQUESTS_COLUMN_SELECT = ['datetime', 'user_id', 'query_string', 'remote_ip', 'url']