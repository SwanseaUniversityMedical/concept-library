from markdown.extensions import Extension
from markdown.postprocessors import Postprocessor

import re

class StrikethroughPostProcessor(Postprocessor):
	"""Strikethrough post-processor"""
	pattern = re.compile(r'[~]{1,2}(((?![~]{1,2}).)+)[~]{1,2}')

	def run(self, html):
		"""Finds instances requiring processing"""
		return re.sub(self.pattern, StrikethroughPostProcessor.process, html)

	@staticmethod
	def process(match):
		"""Processes matched content, encapsulating each with a `<sdel />` HTML element"""
		return f'<del>{match.group(1)}</del>'

class StrikethroughExtension(Extension):
	"""Extends Markdown to add a `<s /> | <del />` strikethrough post-processor"""

	def extendMarkdown(self, md):
		"""Registers the strikethrough postprocessor"""
		md.postprocessors.register(StrikethroughPostProcessor(md), 'strikethrough', 105)

def makeExtension(*args, **kwargs):
	"""See reference @ https://python-markdown.github.io/extensions/api/#dot_notation"""
	return StrikethroughExtension(*args, **kwargs)
