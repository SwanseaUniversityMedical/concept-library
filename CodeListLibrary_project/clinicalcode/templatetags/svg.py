from django import template
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.safestring import mark_safe
from django.contrib.staticfiles import finders

import os
import logging

logger = logging.getLogger(__name__)
register = template.Library()

@register.simple_tag
def svg(target):
  if not isinstance(target, str) or len(target.strip()) < 1 or target.isspace():
    message = 'Expected SVG target to reference a valid, non-empty string but got \'%s\' of type %s' % (str(target), type(target),)
    if settings.DEBUG:
      raise TypeError(message)

    logger.warning(message)
    return ''

  svg_dirs = getattr(settings, 'SVG_DIRS', None)
  svg_file = os.path.splitext(target)[0] + '.svg'

  svg_path = None
  if svg_dirs is None:
    svg_path = finders.find(
      os.path.join('svg', svg_file),
      all=True
    )
  elif isinstance(svg_dirs, list):
    for index, directory in enumerate(svg_dirs):
      if not isinstance(directory, str):
        raise ImproperlyConfigured('Expected SVG_DIRS as list of strings but got %s at index %d' % (type(svg_dirs), index,))

      path = os.path.join(directory, svg_file)
      if os.path.isfile(path):
        svg_path = path
        break
  else:
      raise ImproperlyConfigured('Expected SVG_DIRS as type of list but got %s' % (type(svg_dirs),))

  if svg_path is None or (isinstance(svg_path, (list, tuple)) and len(svg_path) < 1):
    message = 'SVG \'%s\' not found' % (svg_file,)
    if settings.DEBUG:
      raise FileNotFoundError(message)

    logger.warning(message)
    return ''

  try:
    if isinstance(svg_path, (list, tuple)):
      svg_path = svg_path[0]

    with open(svg_path) as f:
      svg = mark_safe(f.read())
  except Exception as e:
    if settings.DEBUG:
      raise e

    logger.warning('Failed to read SVG at \'%s\' with error: %s' % (svg_file,str(e),))
    return ''

  return svg
