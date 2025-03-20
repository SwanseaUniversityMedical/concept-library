'''See: https://kclhi.org/phenoflow/'''
from typing import Any, Dict

import json
import requests


def get_workflow(group: Dict[str, Any]) -> tuple[Dict[str, Any] | None, str | None]:
  '''
    Attempts to resolve the Phenoflow from the specified Phenotype

    Args:
      group (dict): some Phenotype-Phenoflow group

    Returns:
      A tuple variant specifying the resulting workflow and/or an err msg, if applicable
  '''
  legacy_id = group.get('phenoflow_id')
  phenotypes = group.get('related_phenotypes')
  if not isinstance(legacy_id, int) or not isinstance(phenotypes, list):
    return None, f'Workflow {repr(group)} is invalid, expected `related_phenotypes` as `list` type and property `phenoflow_id` to be an int'

  result = None
  for pheno in phenotypes:
    pheno_id = pheno.get('id')
    if not isinstance(pheno_id, str):
      continue

    try:
      response = requests.post('https://kclhi.org/phenoflow/phenotype/all', headers={'Accept': 'application/json'}, json={'importedId': pheno_id})
      if response.status_code != 200:
        continue

      result = response.json()
      result = result.get('url') if isinstance(result, dict) else None
      if isinstance(result, str):
        break
    except requests.exceptions.ConnectionError:
      return None, 'Failed to retrieve workflows'
    except Exception:
      continue

  if not result:
    return None, f'Failed to resolve Group<target: {repr(group)}>'

  return { 'id': legacy_id, 'url': result }, None


def query_phenoflow(in_fpath: str = './assets/minified.json', out_fpath: str = './.out/phenoflow.json') -> None:
  '''
    Queries an entire Phenotype set to derive the new Phenoflow URL target

    Args:
      in_fpath (str): file path to a JSON file specifying the Phenotypes & Phenoflow relationships; defaults to `./assets/minified.json`
      out_fpath (str): output file path; defaults to `./.out/phenoflow.json`
  '''
  with open(in_fpath) as f:
    groups = json.load(f)

  workflows = []
  for group in groups:
    result, err = get_workflow(group)
    if err is not None:
      continue
    workflows.append(result)

  with open(out_fpath, 'w') as f:
    json.dump(workflows, f, indent=2)


def map_phenoflow(in_fpath: str = './assets/minified.json', trg_fpath: str = './.out/phenoflow.json', out_fpath: str = './.out/mapped.json') -> None:
  '''
    Attempts to map a Phenotype and its assoc. Phenoflow relationships to the newest implementation

    Args:
      in_fpath (str): file path to a JSON file specifying the Phenotypes & Phenoflow relationships; defaults to `./assets/minified.json`
      out_fpath (str): file path to a JSON file specifying the resolved targets; defaults to `./.out/phenoflow.json`
      out_fpath (str): output file path; defaults to `./.out/mapped.json`
  '''
  with open(in_fpath) as f:
    groups = json.load(f)

  with open(trg_fpath) as f:
    relation = json.load(f)

  mapped = {}
  for group in groups:
    phenotypes = group.get('related_phenotypes')
    phenoflow_id = group.get('phenoflow_id')
    if not isinstance(phenotypes, list):
      continue

    mapping = next((x for x in relation if x.get('id') == phenoflow_id), None)
    mapping = mapping.get('url') if isinstance(mapping, dict) else None
    for pheno in phenotypes:
      mapped[pheno.get('id')] = { 'source': phenoflow_id, 'target': mapping }

  with open(out_fpath, 'w') as f:
    json.dump(mapped, f, indent=2)


if __name__ == '__main__':
  query_phenoflow()
  map_phenoflow()
