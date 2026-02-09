# Investigation: OMOP Transformation

> [!TIP]  
> Content retrievable from [Athena](https://athena.ohdsi.org/vocabulary/list).

Bundle Composition:

| ID | CDM   | Name                                                                                                   | Code (cdm v5) |
|----|-------|--------------------------------------------------------------------------------------------------------|---------------|
| 1  | CDM 5 | Systematic Nomenclature of Medicine - Clinical Terms (IHTSDO)                                          | SNOMED        |
| 2  | CDM 5 | International Classification of Diseases, Ninth Revision, Clinical Modification, Volume 1 and 2 (NCHS) | ICD9CM        |
| 3  | CDM 5 | International Classification of Diseases, Ninth Revision, Clinical Modification, Volume 3 (NCHS)       | ICD9Proc      |
| 17 | CDM 5 | NHS UK Read Codes Version 2 (HSCIC)                                                                    | Read          |
| 18 | CDM 5 | Oxford Medical Information System (OCHP)                                                               | OXMIS         |
| 55 | CDM 5 | OPCS Classification of Interventions and Procedures version 4 (NHS)                                    | OPCS4         |
| 70 | CDM 5 | International Classification of Diseases, Tenth Revision, Clinical Modification (NCHS)                 | ICD10CM       |

Resultset:

| Total Phenotypes | Total Mapped | Map Rate | Avg Excl. Code Map Rate | Avg Incl. Code Map Rate |
|-----------------:|-------------:|---------:|------------------------:|------------------------:|
|            7,578 |        6,884 |   90.84% |                  77.66% |                  75.63% |

## 1. Tables

> [!TIP]  
> See ref @ [OHDSI Docs](https://www.ohdsi.org/web/wiki/doku.php?id=documentation:cdm:single-page)

> [!CAUTION]  
> The following files have undergone transformation from `tsv` to `csv` via PowerShell, _e.g._:
> ```ps
> Import-Csv -Path '.project/data/VOCABULARY.csv' -Delimiter "`t" | Export-Csv -Path '.project/out/VOCABULARY.csv' -Encoding UTF8 -NoTypeInformation
> ```

> [!CAUTION]  
> Note that `omop.relationships.csv` has modified the header & YYYMMDD date format of `CONCEPT_RELATIONSHIP.csv` using the following:
> ```ps
> Import-CSV `
>     -Path 'CONCEPT_RELATIONSHIP.csv' `
>     -Header "code0_id","code1_id","relationship","valid_start_date","valid_end_date","invalid_reason" `
>   | select -skip 1 `
>   | Foreach-Object {
>     $_.'valid_start_date' = $($_.'valid_start_date' -replace '(?<year>\d{4})(?<month>\d{2})(?<day>\d{2})', '${year}-${month}-${day}')
>     $_.'valid_end_date' = $($_.'valid_end_date' -replace '(?<year>\d{4})(?<month>\d{2})(?<day>\d{2})', '${year}-${month}-${day}')
>     $_
>   } `
>   | Export-CSV -Path 'omop.relationships.csv' -Encoding UTF8 -NoTypeInformation
> ```

### 1.1. Base Tables

#### `data/CONCEPT.csv`

| Field              | Required | Type           | Description                                                                                                                                                                                                                                                             |
|--------------------|----------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `concept_id`       | Yes      | `integer`      | A unique identifier for each Concept across all domains.                                                                                                                                                                                                                |
| `concept_name`     | Yes      | `varchar(255)` | An unambiguous, meaningful and descriptive name for the Concept.                                                                                                                                                                                                        |
| `domain_id`        | Yes      | `varchar(20)`  | A foreign key to the DOMAIN table the Concept belongs to.                                                                                                                                                                                                               |
| `vocabulary_id`    | Yes      | `varchar(20)`  | A foreign key to the VOCABULARY table indicating from which source the Concept has been adapted.                                                                                                                                                                        |
| `concept_class_id` | Yes      | `varchar(20)`  | The attribute or concept class of the Concept. Examples are “Clinical Drug”, “Ingredient”, “Clinical Finding” etc.                                                                                                                                                      |
| `standard_concept` | No       | `varchar(1)`   | This  flag determines where a Concept is a Standard Concept, i.e. is used in  the data, a Classification Concept, or a non-standard Source Concept.  The allowables values are 'S' (Standard Concept) and 'C' (Classification  Concept), otherwise the content is NULL. |
| `concept_code`     | Yes      | `varchar(50)`  | The  concept code represents the identifier of the Concept in the source  vocabulary, such as SNOMED-CT concept IDs, RxNorm RXCUIs etc. Note that  concept codes are not unique across vocabularies.                                                                    |
| `valid_start_date` | Yes      | `date`         | The  date when the Concept was first recorded. The default value is  1-Jan-1970, meaning, the Concept has no (known) date of inception.                                                                                                                                 |
| `valid_end_date`   | Yes      | `date`         | The  date when the Concept became invalid because it was deleted or  superseded (updated) by a new concept. The default value is 31-Dec-2099,  meaning, the Concept is valid until it becomes deprecated.                                                               |
| `invalid_reason`   | No       | `varchar(1)`   | Reason  the Concept was invalidated. Possible values are D (deleted), U  (replaced with an update) or NULL when valid_end_date has the default  value.                                                                                                                  |

#### `data/DOMAIN.csv`

| Field               | Required | Type           | Description                                                                                                                 |
|---------------------|----------|----------------|-----------------------------------------------------------------------------------------------------------------------------|
| `domain_id`         | Yes      | `varchar(20)`  | A unique key for each domain.                                                                                               |
| `domain_name`       | Yes      | `varchar(255)` | The name describing the Domain, e.g. “Condition”, “Procedure”, “Measurement” etc.                                           |
| `domain_concept_id` | Yes      | `integer`      | A foreign key that refers to an identifier in the CONCEPT table for the unique Domain Concept the Domain record belongs to. |

#### `data/VOCABULARY.csv`

| Field                   | Required | Type           | Description                                                                                                                                                      |
|-------------------------|----------|----------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `vocabulary_id`         | Yes      | `varchar(20)`  | A unique identifier for each Vocabulary, such as ICD9CM, SNOMED, Visit.                                                                                          |
| `vocabulary_name`       | Yes      | `varchar(255)` | The  name describing the vocabulary, for example “International  Classification of Diseases, Ninth Revision, Clinical Modification,  Volume 1 and 2 (NCHS)” etc. |
| `vocabulary_reference`  | Yes      | `varchar(255)` | External reference to documentation or available download of the about the vocabulary.                                                                           |
| `vocabulary_version`    | Yes      | `varchar(255)` | Version of the Vocabulary as indicated in the source.                                                                                                            |
| `vocabulary_concept_id` | Yes      | `integer`      | A  foreign key that refers to a standard concept identifier in the CONCEPT  table for the Vocabulary the VOCABULARY record belongs to.                           |

#### `data/RELATIONSHIP.csv`

| Field                     | Required | Type           | Description                                                                                                                                                             |
|---------------------------|----------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `relationship_id`         | Yes      | `varchar(20)`  |  The type of relationship captured by the relationship record.                                                                                                          |
| `relationship_name`       | Yes      | `varchar(255)` |  The text that describes the relationship type.                                                                                                                         |
| `is_hierarchical`         | Yes      | `varchar(1)`   | Defines  whether a relationship defines concepts into classes or hierarchies.  Values are 1 for hierarchical relationship or 0 if not.                                  |
| `defines_ancestry`        | Yes      | `varchar(1)`   | Defines  whether a hierarchical relationship contributes to the concept_ancestor  table. These are subsets of the hierarchical relationships. Valid  values are 1 or 0. |
| `reverse_relationship_id` | Yes      | `varchar(20)`  | The identifier for the relationship used to define the reverse relationship between two concepts.                                                                       |
| `relationship_concept_id` | Yes      | `integer`      | A foreign key that refers to an identifier in the CONCEPT table for the unique relationship concept.                                                                    |

### 1.2. Concept Tables

#### `data/CONCEPT_CLASS.csv`

| Field                      | Required | Type           | Description                                                                                                         |
|----------------------------|----------|----------------|---------------------------------------------------------------------------------------------------------------------|
| `concept_class_id`         | Yes      | `varchar(20)`  | A unique key for each class.                                                                                        |
| `concept_class_name`       | Yes      | `varchar(255)` | The name describing the Concept Class, e.g. “Clinical Finding”, “Ingredient”, etc.                                  |
| `concept_class_concept_id` | Yes      | `integer`      | A foreign key that refers to an identifier in the CONCEPT table for the unique Concept Class the record belongs to. |

#### `data/CONCEPT_SYNONYM.csv`

| Field                  | Required | Type            | Description                                           |
|------------------------|----------|-----------------|-------------------------------------------------------|
| `concept_id`           | Yes      | `integer`       | A foreign key to the Concept in the CONCEPT table.    |
| `concept_synonym_name` | Yes      | `varchar(1000)` | The alternative name for the Concept.                 |
| `language_concept_id`  | Yes      | `integer`       | A foreign key to a Concept representing the language. |

#### `data/CONCEPT_RELATIONSHIP.csv`

| Field              | Required | Type          | Description                                                                                                                                                                       |
|--------------------|----------|---------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `concept_id_1`     | Yes      | `integer`     | A foreign key to a Concept in the CONCEPT  table associated with the relationship. Relationships are directional,  and this field represents the source concept designation.      |
| `concept_id_2`     | Yes      | `integer`     | A foreign key to a Concept in the CONCEPT  table associated with the relationship. Relationships are directional,  and this field represents the destination concept designation. |
| `relationship_id`  | Yes      | `varchar(20)` | A unique identifier to the type or nature of the Relationship as defined in the RELATIONSHIP table.                                                                               |
| `valid_start_date` | Yes      | `date`        | The date when the instance of the Concept Relationship is first recorded.                                                                                                         |
| `valid_end_date`   | Yes      | `date`        | The  date when the Concept Relationship became invalid because it was  deleted or superseded (updated) by a new relationship. Default value is  31-Dec-2099.                      |
| `invalid_reason`   | No       | `varchar(1)`  | Reason  the relationship was invalidated. Possible values are 'D' (deleted),  'U' (replaced with an update) or NULL when valid_end_date has the  default value.                   |

#### `data/CONCEPT_ANCESTOR.csv`

| Field                      | Required | Type      | Description                                                                                                                                                             |
|----------------------------|----------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ancestor_concept_id`      | Yes      | `integer` | A foreign key to the concept in the concept table for the higher-level concept that forms the ancestor in the relationship.                                             |
| `descendant_concept_id`    | Yes      | `integer` | A foreign key to the concept in the concept table for the lower-level concept that forms the descendant in the relationship.                                            |
| `min_levels_of_separation` | Yes      | `integer` | The  minimum separation in number of levels of hierarchy between ancestor  and descendant concepts. This is an attribute that is used to simplify  hierarchic analysis. |
| `max_levels_of_separation` | Yes      | `integer` | The  maximum separation in number of levels of hierarchy between ancestor  and descendant concepts. This is an attribute that is used to simplify  hierarchic analysis. |

## 2. Source to Concept Map

> [!TIP]  
> See ref @ [`source_to_concept_map`](https://www.ohdsi.org/web/wiki/doku.php?id=documentation:cdm:source_to_concept_map)

### 2.1. Data Model

| Field                     | Required | Type           | Description                                                                                                                                                     |
|---------------------------|----------|----------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `source_code`             | Yes      | `varchar(50)`  | The source code being translated into a Standard Concept.                                                                                                       |
| `source_concept_id`       | Yes      | `integer`      | A foreign key to the Source Concept that is being translated into a Standard Concept.                                                                           |
| `source_vocabulary_id`    | No       | `varchar(20)`  | A foreign key to the VOCABULARY table defining the vocabulary of the source code that is being translated to a Standard Concept.                                |
| `source_code_description` | Yes      | `varchar(255)` | An  optional description for the source code. This is included as a  convenience to compare the description of the source code to the name of  the concept.     |
| `target_concept_id`       | Yes      | `integer`      | A foreign key to the target Concept to which the source code is being mapped.                                                                                   |
| `target_vocabulary_id`    | Yes      | `varchar(20)`  | A foreign key to the VOCABULARY table defining the vocabulary of the target Concept.                                                                            |
| `valid_start_date`        | Yes      | `date`         | The date when the mapping instance was first recorded.                                                                                                          |
| `valid_end_date`          | Yes      | `date`         | The  date when the mapping instance became invalid because it was deleted or  superseded (updated) by a new relationship. Default value is  31-Dec-2099.        |
| `invalid_reason`          | No       | `varchar(1)`   | Reason  the mapping instance was invalidated. Possible values are D (deleted), U  (replaced with an update) or NULL when valid_end_date has the default  value. |

### 2.2. Alternative Mapping

#### 2.2.1. ICD

> [!TIP]  
> 1. Hover `Info` tab
> 2. Click `ICD-10 / ICD-11 mapping tables` to download

Download: [ICD-10 / ICD-11 mapping tables](https://icd.who.int/browse/2025-01/mms/en)

#### 2.2.2. BNF via dm+d

Download: [BNF to dm+d](https://www.bennett.ox.ac.uk/blog/2023/11/bnf-to-dictionary-of-medicines-and-devices-dm-d-map-now-available/)

#### 2.2.3. Read Code V3 via SNOMED

Download:
- [ReadV2<->V3 crossmap](https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/9/items/255/releases)
- [ReadV3<->SNOMED crossmap](https://isd.digital.nhs.uk/trud/users/guest/filters/0/categories/38/items/270/)
