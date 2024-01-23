# 1. Template documentation
>***[!] Note:** An example can be found within `./clinical_coded_phenotype.json`*  

## 1.1 `template_details`

Used to define the base details of a template:
1. `version` - defines the current version of the phenotype. This value is read by the model manager when the template is saved and updates the datamodel to the version defined within the template
2. `name` - the name of the template, which is used by django's templates to present the name in a user-friendly manner
3. `description` - read by the model manager to update the datamodel's description field, and is sometimes used by django's templates to present the description
4. `card_type` - defines the `.html` file used by the search renderer to present the phenotype as a search result, found within `cll/templates/components/search/cards/[card_type].html`

```json
{
  "template_details": {
    "version": 1,
    "name": "Clinical-Coded Phenotype",
    "description": "Phenotype definitions that are based on lists of clinical codes, or algorithms using clinical codes.",
    "card_type": "clinical"
  },
}
```

## 1.2 `sections`

Used by both the `./create` and `./detail` pages to separate the pages into human readable sections, properties include:
1. `title` - defines the section's title
2. `description` - defines the section's description; if this isn't present, the description will not be rendered
3. `fields` - defines the `fields` that are included within this section
4. `hide_on_create` or `hide_on_detail` - hides this section within the relative page
5. `hide_if_empty` - this forcefully hides the section on the `./detail` page if the fields contained within it resolve to null values
6. `do_not_show_in_production` - forcefully hides the section on the `./detail` page on the production site, used to toggle experimental sections
7. `requires_auth` - forcefully hides the section if the user viewing it isn't authenticated (only present on `./detail` page)
8. `documentation` - defines the documentation page to render for this section; this is viewable via the interface, and reflects the documentation as defined within `DocumentationViewer.py`

```json
{
  "sections": [
    {
      "title": "Name & Author",
      "description": "",
      "fields": ["name", "author"],
      "hide_on_detail": true
    }
  ]
}
```

## 1.3 `fields`

This defines all of the fields that are able to be recorded within the template, aside from those that are derived from the metadata template. The order of these items are preserved - this is saved as the `layout_order` property within each field when the datamodel is saved via the model manager.

### 1.3.1 Base properties
>***[!] Note:** The key of each object defines its field name within the datamodel*  

The properties of each object can include:
1. `title` - mandatory field that describes the human readable name of this field (should relate to its property)
2. `description` - human-readable description of the field; if empty, this can hide the description field for the `./create` page
3. `field_type` - this property defines what type of input/output html snippet is used to interface with this property. How these are resolved can be seen in the `FIELD_TYPES` constant within `./constants.py`
4. `active` - this property overrides the presence of the field within the interface and/or whether a user is able to modify it; when inactive, they will not be present in the interface nor will they be modifiable
5. `requires_auth` - this defines whether the field will be visible to anonymous users or not, either during presentation in the search results or when viewing the model from the `./detail` page
6. `hide_on_create` or `hide_on_detail` - hides this field within the relative page
7. `hide_if_empty` - this forcefully hides the field on the `./detail` page if it resolves to a null or empty value

### 1.3.2 Properties that relate to internal behaviour

There are some properties of a field that have important behaviour that either reflects or determines how it is processed, or re-defines internal behaviour e.g. _how it appears on search, how the data is validated etc_

These fields include:
1. `validation`
    - This object defines how the object is validated, and how it is processed internally; this includes, but is not limited to, how it is processed when saving, how the data is collected and handled via its components, and how it is processed during operations like search
    - The `validation` properties include:
        1. `type` - the data type associated with this field. Please see below for available datatypes, which may require more properties than defined within this list
        2. `mandatory` - whether the field is mandatory, this will abort saves if not present & will inform users when they attempt to save via the interface
        3. `unique` - this forces the field to be unique, similar to the Django behaviour found [here](https://docs.djangoproject.com/en/4.2/ref/models/fields/#unique)
        4. `computed` - these makes it so that the field's value isn't directly defined by the user, instead, when saving/loading the data, the `computed` field forces the lookup/validation methods to compute the field's value based on other values defined by the template and/or by deriving that data from associated data models (e.g. in the case of `brand`, `coding_system` etc)

2. `search`
    - This defines the search-related behaviour of the field; either by showing/hiding its presence on the search page and/or toggling whether it can be filtered via the API
    - The `search` properties include:
        1. `filterable` - determines whether a field is filterable via the search page
        2. `api` - determines whether a field is filterable via the API
        3. `single_search_only` - makes it so this property isn't available on the search page when searching only a single template type; this property is currently deprecated until the new search task is implemented
    - Only specific field datatypes are filterable, these include:
        1. `int` and `enum` - either via their `option` or `source` definitions - see below for more information
        2. `int_array` - via its associated models defined by its `source`
        3. `datetime` - compares the top-level metadata datetime field with the input value
        4. `string` - compares either template or top-level metadata literally

### 1.3.3 Example
See below, where we've defined a `string` datatype example using a length and a regex in its validation and have made it filterable within the API:
```json
{
  "some_example": {
    "title": "Example",
    "description": "Some example field",
    "field_type": "string_inputbox",
    "active": false,
    "validation": {
      "type": "string",
      "mandatory": false,
      "length": [0, 250],
      "regex": "(?:\\d+\/|\\d+)+[\\s+]?-[\\s+]?(?:\\d+\/|\\d+)+"
    },
    "search": {
      "api": true
    },
    "hide_on_create": true,
    "hide_if_empty": true
  }
}
```

## 1.4 Available datatypes

### 1.4.1 Base datatypes
1. `string` - defines a `str()` datatype, modifiers include:
    - `regex` - optionally defines a regex validation string to be checked against the input value when saving
    - `length` - optionally defines the minimum and maximum length of the input value when saving (defined as an array with two values, the first denoting its minimum size and the latter defining its maximum size)
2. `string_array` - defines a `Array[str()]` datatype
    - _No modifiers currently implemented_
3. `int` - defines an `int` datatype, modifiers include:
    - `range` - optionally defines the minimum and maximum value of the input value when saving; the first and second values of this array defines the lower and upper bounds of the number such that `arr[1] <= x <= arr[2]`
    - `source` - used to define the source model of this integer, where the value is treated as an index (or id) of an associated datamodel - see below for more details
4. `int_array` - defines an `Array[int]` datatype, modifiers include:
    - `source` - used to define the source model of this array of integers, where each value of the array is treated as an index (or id) of an associated model   - see below for more details
5. `enum` - used to define an `enum.Enum()` datatype, modifiers include:
    - `options` - describes an key-value pair object, where each key defines the index and each value defines the value associated with the option (should be human readable). The value is validated by comparing its index against the the `option` dictionary and confirming its presence
6. `datetime`
    - **Note:** only partial implementation, not currently available for templates; currently we're using the validation for dates as a `string` - this is a side effect of legacy Phenotype models accepting strings as a valid date, which has resulted in an issue with parsing legacy dates as a valid `datetime`

### 1.4.2 Template specific datatypes
1. `concept` - used to define an array of dictionaries, containing information relating to the `concept_id` and `concept_version_id` of a concept associated with the phenotype and its template
    - Data example:
      - Both `concept_id` and `concept_version_id` are expected to be the `int` datatype
    ```json
    [
      {
        "concept_id": 1,
        "concept_version_id": 1
      }
    ]
    ```
    - Properties include:
        - `has_children` - this property is required and flags it as a property with children (or in this case, an associated datamodel), so that the model information can be derived for the phenotype as a whole
2. `publication` - used to define an array of dictionaries containing publication related information
    - Data example:
      - Both `details` and `doi` are expected to be the `str` datatype - you should note that the `DOI` field can be `null` or empty, but when present as `str` it will have been validated with a regex match
      ```json
      [
        {
          "details": "some human readable publication",
          "doi": "[some_doi_that_matches_regex]"
        }
      ]
      ```
    - Properties include:
      - _No current modifiers implemented_

### 1.4.3 `source` definitions
This property defines the association of a field with a datamodel, its functionality and behaviour can be modified by the following properties:

1. `table` - defines the associated table
2. `query` - defines the datamodel's field to query during operations such as: search, when collecting & validating the data and so forth
3. `relative` - defines the datamodel's field that's used to return a human readable value for presentation to the user
4. `filter` - used to define additional filters used during operations such as: query, search, when collecting & validating the data etc
    - `{some_value}` - this is inputted literally into the query operation, e.g. `"tag_type": 1` would force a Django ORM based filter like so: `Table.objects.filter(tag_type=1)`
    - `source_by_brand` - this performs an additional operation on the query to filter the output values by its associated brand (e.g. in the case of `collections`, which has an associated `brand`)
5. `include` - an array of strings that pulls related fields into the final output
    - e.g. in the case of `"include": ["uid", "name"]` the resulting object would include the `query` field and its value, the `relative` field and its value, as well as any included in the `include` array

An example of a field containing a source definition could look like the following:
- Resulting object (as processed by the template example below):
  ```json
  [
    {
      "name": "[value retrieved from 'relative']",
      "value": 1,
      "uid": 1,
      "url": "http://someexample.org"
    }
  ]
  ```
- The template could look like this:
  ```json
  {
    "some_source_example": {
      "title": "Example source",
      "description": "Some example sourced datatype",
      "field_type": "[some field type component]",
      "active": true,
      "validation": {
        "type": "int_array",
        "mandatory": false,
        "source": {
          "table": "SomeTable",
          "query": "id",
          "relative": "sone_field_associated_with_a_string_name",
          "include": ["uid", "url"]
        }
      },
      "search": {
        "filterable": true,
        "api": true
      }
    },
  }
  ```

# 2 Metadata documentation
>***[!] Note:** The metadata fields can be found within `./constants.py`*  

## 2.1 `metadata`
The `metadata` constant within `./constants.py` defines the fields that relate to metadata, which we have defined as fields that are either relevant to every type of phenotype, or as internal data points that we would like to measure and record - these should be considered as fields that are associated with every `template`.

Specific metadata-related properties include:
1. `ignore` - this ignores the property when performing merge operations on the metadata and its associated template (see `./template_utils.py`)
2. `is_base_field` - this should be included with every field that is mergeable (i.e. any that aren't flagged with the `ignore` property) as it is used to differentiate between metadata & template fields during operations where the user has sent the app a merged definition (e.g. in the case of API and/or create page)

```python
metadata = {
  'template': {
    'title': 'Type',
    'field_type': '???',
    'active': True,
    'validation': {
      'type': 'int',
      'mandatory': True,
      'computed': True,
      'source': {
        'table': 'Template',
        'query': 'id',
        'relative': 'name'
      }
    },
    'search': {
      'filterable': True,
      'single_search_only': True,
    },
    'ignore': True
  },
}
```

## 2.2 `FIELD_TYPES`
>***[!] Note:** There are some fields present within the `FIELD_TYPES` constant that are currently unused, e.g. `max_length`, `display`, `use_permitted_values` etc - these are intended to modify the behaviour of the component, but are not yet fully implemented - this was being worked on by @elmessary, unsure if we're still continuing with this task*  

Defines the input/output components used by the HTML (via Django templatetag renderers) to build the interface for the defined template, where:

1. `data_type` - defines the expected datatype. However, it's important to note: this is currently unused, only used for documentation reference
2. `input_type` - defines the component used to render the input HTML for this field type, found within `cll/templates/components/create/inputs/[input_type](.html)`
3. `output_type` - defines the component used to render the output HTML for this field type, found within `cll/templates/components/detail/outputs/[output_type](.html)`

```python
FIELD_TYPES = {
  # e.g...
  'int': {
    # defines the expected datatype
    'data_type': 'int',
    # defines the input html component used (e.g. for use on the `./create` page)
    'input_type': 'inputbox',
    # defines the output html component used (e.g. for use on the `./detail` page)
    'output_type': 'inputbox'
  },
}
```
