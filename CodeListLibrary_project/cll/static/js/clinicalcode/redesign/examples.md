# Tagify
A class that transforms a text input into a tag component.

Example usage:
```js
import Tagify from '../components/tagify.js'

const tags = [
  {
    name: 'SomeTagName',
    value: 'SomeTagValue',
  },
  {
    name: 'SomeTagName',
    value: 'SomeTagValue',
  }
];

const tagComponent = new Tagify('phenotype-tags', {
  'autocomplete': true,
  'useValue': false,
  'allowDuplicates': false,
  'restricted': true,
  'items': tags,
});
```

# FuzzyQuery
A static class that uses Levenshtein distance to search a haystack.

Example usage:
```js
import FuzzyQuery from '../components/fuzzyQuery.js'

const haystack = [
  'some_item1',
  'some_item2',
  'another_thing',
  'another_thing_1',
];

const query = 'some_item';
const results = FuzzyQuery.Search(haystack, query, FuzzyQuery.Results.Sort, FuzzyQuery.Transformers.IgnoreCase);
console.log(results); // Will return ['some_item1', 'some_item2']
```