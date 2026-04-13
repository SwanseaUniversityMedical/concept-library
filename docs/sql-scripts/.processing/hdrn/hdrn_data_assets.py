'''See: https://dash.hdrn.ca/en/inventory/'''
from typing import Any, Dict

import os
import re
import json
import datetime

import numpy as np
import pandas as pd

COL_NAMES = ['Name', 'UUID', 'Site', 'Region', 'Data Categories', 'Description', 'Purpose', 'Scope', 'Data Level', 'Collection Period', 'Link', 'Years']

class JsonEncoder(json.JSONEncoder):
  '''Encodes PyObj to JSON serialisable objects, see `jencoder`_

  .. _jencoder: https://docs.python.org/3/library/json.html#json.JSONEncoder
  '''
  def default(self, obj: Any) -> None | Dict[str, str]:
    '''JSON encoder extensible implementation, see `jencoder`_

    Args:
      obj (Any): URL to target resource

    Returns:
      A JSON-encoded object

    .. _jencoder: https://docs.python.org/3/library/json.html#json.JSONEncoder.default
    '''
    if isinstance(obj, (datetime.date, datetime.datetime)):
      return { 'type': 'datetime', 'value': obj.isoformat() }


def tx_link(link: str | None) -> pd.Series:
  '''Parse id & convert links from fmt: `https://www.hdrn.ca/en/inventory/` to `https://dash.hdrn.ca/en/inventory/`

  Args:
    link (str|None): URL to target resource

  Returns:
    A `pd.Series` with the parsed `id` & the transformed `link`, if applicable
  '''
  if isinstance(link, str):
    ident = re.findall(r'(\d+)\/$', link)
    if ident is not None and len(ident) > 0:
      ident = int(ident[-1])
      return pd.Series([
        ident,
        f'https://dash.hdrn.ca/en/inventory/{ident}/'
      ])

  return pd.Series([None, None])


def build_pkg(inv_path: str ='./assets/HDRN_CanadaInventoryList.xlsx', out_fpath: str = './.out/HDRN_Data.json') -> None:
  '''Builds the HDRN Data Asset JSON packet

  Note:
    XLSX file located @ `inv_path` expects the following shape:
      - Sheet: `Inventory`
      - Headers: `Name | UUID | Site | Region | Data Categories | Description | Purpose | Scope | Data Level | Collection Period | Link | Years | Created Date | Modified By`

  Args:
    inv_path (str): path to inventory list; defaults to `./assets/HDRN_CanadaInventoryList.xlsx`
    out_fpath (str): output file path; defaults to `./.out/HDRN_Data.json`
  '''
  # Process data
  pkg = pd.read_excel(inv_path, sheet_name='Inventory')
  pkg = pkg.replace({ np.nan: '' })

  pkg[COL_NAMES] = pkg[COL_NAMES].astype(str)
  pkg = pkg.replace(r'^\s*$', None, regex=True)

  pkg[['Id', 'Link']] = pkg.apply(lambda x: tx_link(x['Link']), axis=1)
  pkg['Created Date'] = pd.to_datetime(pkg['Created Date'], format='%Y-%m-%d %H:%M:%S')
  pkg['Modified By'] = pd.to_datetime(pkg['Created Date'], format='%Y-%m-%d %H:%M:%S')

  pkg = pkg.rename(columns={'Modified By': 'Modified Date'})
  pkg = pkg.sort_values(by='Created Date', axis=0, ascending=True, ignore_index=True)

  pkg.columns = [x.strip().replace(' ', '_').lower() for x in pkg.columns]

  # Compute unique categorical data
  unq_sites = pkg['site'].str.split(r'(?:;)\s*').dropna().to_numpy()
  unq_sites = np.unique(sum(unq_sites, []))

  unq_cats = pkg['data_categories'].str.split(r'(?:,|;)\s*').dropna().to_numpy()
  unq_cats = np.unique(sum(unq_cats, []))
  unq_cats = np.strings.capitalize(unq_cats)

  # Save pkg
  dpath = os.path.realpath(os.path.dirname(out_fpath))
  if not os.path.exists(dpath):
    os.makedirs(dpath)

  pkg = pkg.to_dict('records')
  pkg = {
    'assets': pkg,
    'metadata': {
      'site': list(unq_sites),
      'data_categories': list(unq_cats),
    },
  }

  with open(out_fpath, 'w') as f:
    json.dump(pkg, f, cls=JsonEncoder)


if __name__ == '__main__':
  build_pkg()
