from faker import Faker

import json

from . import utils
from . import constants

class Graph:
    """
      [!] Note: see utils.py for kwargs to change size / connectivity

      e.g.

        ```py
        # Generate a graph
        graph = Graph.generate(graph_type=Graph.Types.DirectedAcyclicGraph) # or Graph.generate(graph_type=Graph.Types.Tree)

        # `graph.dots` - can be used to generate the edge list in DOT format, ref @ https://en.wikipedia.org/wiki/DOT_(graph_description_language
        print(graph.dots)

        # `graph.nodes` - provides the fake data associated with each node and its edge list
        print(graph.nodes)

        # `graph.dump` - dump to file if needed
        graph.dump(output_file='./test.json')
        ```

    """

    __key = object()

    @classmethod
    def generate(cls, graph_type, **kwargs):
        return Graph(cls.__key, graph_type, **kwargs)

    @classmethod
    @property
    def Types(cls):
        return constants.GraphTypes

    def __init__(self, key, graph_type, **kwargs):
        if key != Graph._Graph__key:
            raise AssertionError('Constructor is private, please use the `generate` method')

        if graph_type == constants.GraphTypes.DirectedAcyclicGraph:
            self.network = utils.generate_dag(**kwargs)
        elif graph_type == constants.GraphTypes.Tree:
            self.network = utils.generate_tree(**kwargs)
        else:
            raise NotImplementedError('Graph type is not implemented')
        self.type = graph_type

    @property
    def dots(self):
        dots = ''
        for edge in self.network:
            dots += '\t%(index)s -> %(vertex)s;\n' % { 'index': edge[0], 'vertex': edge[1] }

        return 'digraph {\n%s}' % dots 

    @property
    def nodes(self):
        fake = Faker()
        nodes = [ ]
        for edge in self.network:
            node = next((x for x in nodes if x['id'] == edge[0]), None)
            if not node:
                node = { 'id': edge[0], 'name': fake.name(), 'edges': [ ] }
                nodes.append(node)

            connection = next((x for x in nodes if x['id'] == edge[1]), None)
            if not connection:
                nodes.append({ 'id': edge[1], 'name': fake.name(), 'edges': [ ] })

            node['edges'].append(edge[1])

        return nodes
    
    def dump(self, output_file=None, indent=2):
        nodes = self.nodes
        if isinstance(output_file, str):
            with open(output_file, 'w') as f:
                json.dump(nodes, f, indent=indent)

        return json.dumps(nodes, indent=indent)
