from django.core.management.base import BaseCommand
from django.db import transaction, connection

import re
import os
import json
import enum
import time

from ...generators.graphs.generator import Graph as GraphGenerator
from ...models.CodingSystem import CodingSystem
from ...models.ClinicalDiseaseCategory import ClinicalDiseaseCategoryEdge, ClinicalDiseaseCategoryNode


######################################################
#                                                    #
#                     Constants                      #
#                                                    #
######################################################
class IterableMeta(enum.EnumMeta):
    """
        Metaclass that defines additional methods
        of operation and interaction with enums

    """
    def from_name(cls, name):
        if name in cls:
            return getattr(cls, name)
    
    def __contains__(cls, lhs):
        try:
            cls(lhs)
        except ValueError:
            return lhs in cls.__members__.keys()
        else:
            return True

class GraphType(int, enum.Enum, metaclass=IterableMeta):
    """
        Parsed from input file to determine how to handle the data
        
        e.g. { type: 'CODE_CATEGORIES' } within `./data/graphs/icd10_categories.json`

    """
    CODE_CATEGORIES = 0

class LogType(int, enum.Enum, metaclass=IterableMeta):
    """
        Enum that reflects the output style, as described by the BaseCommand log style

        See ref @ https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/#django.core.management.BaseCommand.style

    """
    SUCCESS = 1
    NOTICE = 2
    WARNING = 3
    ERROR = 4


######################################################
#                                                    #
#                   Graph Builders                   #
#                                                    #
######################################################
class GraphBuilders:
    """
        Builds a graph according to the given GraphType
        and its associated data

    """

    @classmethod
    def try_build(cls, builder_type, data):
        """
            Attempts to build a graph given a valid builder type

        """
        if not isinstance(builder_type, GraphType):
            return False, 'Expected valid GraphType, got %s' % str(builder_type)

        desired_builder = getattr(cls, builder_type.name)
        if desired_builder is None:
            return False, 'Invalid Builder, no class method available with the name: %s' % builder_type.name

        bound_to = getattr(desired_builder, '__self__', None)
        if not isinstance(bound_to, type) or bound_to is not cls:
            return False, 'Invalid Builder, no appropriate class method found for BuilderType<%s>' % builder_type.name

        return desired_builder(data)

    @classmethod
    def CODE_CATEGORIES(cls, data):
        """
            ICD-10 Disease Category builder test(s)

        """

        ''' [!] Warning: This is only partially optimised '''
        if not isinstance(data, list):
            return False, 'Invalid data type, expected list but got %s' % type(data)

        # process nodes
        nodes = [ ]
        linkage = [ ]
        result = [ ]
        name_hashmap = { }
        started = time.time()

        def create_linkage(parent, parent_index, children):
            for child_data in children:
                name = child_data.get('name').strip()
                code = child_data.get('code').strip()

                # ICD-10 uses non-unique names, add code to vary them if required
                if name in name_hashmap:
                    name = f'{name} ({code})'
                name_hashmap[name] = True

                # Create child node and process descendants
                node = ClinicalDiseaseCategoryNode(name=name, code=code)
                index = len(nodes)
                nodes.append(node)
                linkage.append([parent_index, index])

                descendants = child_data.get('children')
                child_count = len(descendants) if isinstance(descendants, list) else 0
                result.append(f'\t\tChildNode<name: {node.name}, code: {node.code}, children: {child_count}>')

                if isinstance(descendants, list):
                    create_linkage(node, index, descendants)

        for root_data in data:
            # clean up the section name(s)
            root_name = root_data.get('name').strip()
            matched_code = re.search(r'(\b(?=[a-zA-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*-\b(?=[A-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*)', root_name)

            root_name = re.sub(r'\((\b(?=[a-zA-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*-\b(?=[A-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*)\)', '', root_name).strip()
            derived_code = matched_code.group() if matched_code else None

            # process node and its branches
            root = ClinicalDiseaseCategoryNode(name=root_name, code=derived_code)
            index = len(nodes)
            nodes.append(root)

            children = root_data.get('sections')
            result.append(f'\tRootNode<name: {root.name}, code: {root.code}, children: {len(children)}>')

            create_linkage(root, index, children)

        # bulk create nodes & children
        nodes = ClinicalDiseaseCategoryNode.objects.bulk_create(nodes)

        # bulk create edges
        ClinicalDiseaseCategoryNode.children.through.objects.bulk_create(
            [
                # list comprehension here is required because we need to match the instance(s)
                ClinicalDiseaseCategoryNode.children.through(
                    name=f'{nodes[link[0]].name} | {nodes[link[1]].name}',
                    parent=nodes[link[0]],
                    child=nodes[link[1]]
                )
                for link in linkage
            ],
            batch_size=7000
        )

        # update coding system and apply related code
        icd_10_id = CodingSystem.objects.get(name='ICD10 codes').id

        with connection.cursor() as cursor:
            ''' [!] Note: We could probably optimise this '''

            sql = """
            -- update matched values
            update public.clinicalcode_clinicaldiseasecategorynode as trg
               set coding_system_id = %(coding_id)s,
                   code_id = src.code_id
              from (
                select node.id as node_id,
                       code.id as code_id
                  from public.clinicalcode_clinicaldiseasecategorynode as node
                  join public.clinicalcode_icd10_codes_and_titles_and_metadata as code
                    on node.code = code.code
              ) src
             where trg.id = src.node_id;

            -- update null values
            update public.clinicalcode_clinicaldiseasecategorynode as trg
               set coding_system_id = %(coding_id)s
             where coding_system_id is null;
            """
            cursor.execute(sql, { 'coding_id': icd_10_id })

        # create result string for log
        elapsed = (time.time() - started)
        result = 'Created Nodes<coding_system: %d, elapsed: %.2f s> {\n%s\n}' % (icd_10_id, elapsed, '\n'.join(result))

        return True, result


######################################################
#                                                    #
#                     DAG Command                    #
#                                                    #
######################################################
class Command(BaseCommand):
    help = 'Various tasks associated with the generation of DAGs'

    DEFAULT_FILE = 'data/graphs/categories.json'
    VALID_FILE_TYPES = ['.json']
    LOG_FILE_NAME = 'DAG_LOGS'
    LOG_FILE_EXT = '.txt'

    def __get_log_style(self, style):
        """
            Returns the BaseCommand's log style

            See ref @ https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/#django.core.management.BaseCommand.style

        """
        if isinstance(style, str):
            style = style.upper()
            if style in LogType.__members__:
                return getattr(self.style, style)
        elif isinstance(style, LogType):
            if style.name in LogType.__members__:
                return getattr(self.style, style.name)
        return self.style.SUCCESS

    def __log_dots(self, nodes, name=None):
        """
            Logs the edge list in DOT format

            See ref @ https://en.wikipedia.org/wiki/DOT_(graph_description_language

        """
        name = name or 'Unknown'
        dots = ''
        for i, node in enumerate(nodes):
            for child in node.children.all():
                dots += '\t%(index)s -> %(vertex)s;\n' % { 'index': node.id, 'vertex': child.id }

        self.__log_to_file('Digraph<%s>: digraph {\n%s}' % (name, dots))

    def __log_to_file(self, message, style=LogType.SUCCESS):
        """
            Logs the message, prepended with its style, to the log file (if a valid directory has been provided)

        """
        directory = self._log_dir
        if not isinstance(directory, str):
            return

        if not os.path.isabs(directory):
            directory = os.path.join(
                os.path.abspath(os.path.dirname('manage.py')),
                directory
            )

        if not os.path.exists(directory):
            os.makedirs(directory)

        style = style.name if isinstance(style, LogType) else style
        filename = os.path.join(directory, f'{self.LOG_FILE_NAME}{self.LOG_FILE_EXT}')
        offset = '\n' if os.path.exists(filename) else ''
        with open(filename, 'a') as file:
            file.writelines([f'{offset}[{style}] {message}\n'])

    def __log(self, message, style=LogType.SUCCESS):
        """
            Logs the incoming to:
                1. The log file, if a valid directory has been provided
                2. The terminal, if the `-p` argument has been provided

        """
        self.__log_to_file(message, style)

        if not self._verbose:
            return
        style = self.__get_log_style(style)
        self.stdout.write(style(message))

    def __try_load_file(self, filepath):
        """
            Attempts to load the given filepath as a JSON object

        """
        filepath = os.path.join(
            os.path.abspath(os.path.dirname('manage.py')),
            filepath if filepath is not None else self.DEFAULT_FILE
        )

        self.__log(f'Initialising DAG command with Path<{filepath}> ...')

        if not os.path.exists(filepath):
            self.__log(f'Path<{filepath}> does not exist', LogType.ERROR)
            return

        if not os.path.isfile(filepath):
            self.__log(f'Path<{filepath}> does not reference a file', LogType.ERROR)
            return

        file_extension = os.path.splitext(filepath)[1]
        if file_extension not in self.VALID_FILE_TYPES:
            self.__log(f'File<{filepath}> does not reference a valid file of expected types: {", ".join(self.VALID_FILE_TYPES)}', LogType.ERROR)
            return

        try:
            with open(filepath) as f:
                data = json.load(f)
                return data
        except Exception as e:
            self.__log(f'Error when attempting to load File<{filepath}>:\n{str(e)}', LogType.ERROR)
        return None

    def __try_build_dag(self, filepath):
        """
            Attempts to build the DAG from the given filepath

        """
        # attempt import
        data = self.__try_load_file(filepath)
        if data is None:
            return

        # validate
        graph_input = data.get('data', None)
        if graph_input is None:
            self.__log(f'No property `data` found within File<{filepath}>', LogType.ERROR)
            return

        builder_type = data.get('type', None)
        builder_type = GraphType[builder_type] if builder_type is not None and builder_type in GraphType else None

        if not isinstance(builder_type, GraphType):
            self.__log(f'No valid property `type` found within File<{filepath}>', LogType.ERROR)
            return

        # attempt generation
        success, result = GraphBuilders.try_build(builder_type, graph_input)
        if not success:
            result = result if isinstance(result, str) else 'Unknown error occurred'
            self.__log(f'Error occurred when processing File<{filepath}> via BuilderType<{builder_type.name}>:\n\t{result}', LogType.ERROR)
            return

        self.__log('Building Graph from File<%s> was completed successfully' % filepath, LogType.SUCCESS)

        if isinstance(result, str):
            self.__log(result, LogType.SUCCESS)

    def __generate_debug_dag(self):
        """
            Responsible for generating a debug dag using the graph generators & its utility methods

        """
        graph = GraphGenerator.generate(graph_type=GraphGenerator.Types.DirectedAcyclicGraph)
        nodes = [ClinicalDiseaseCategoryNode(name=node.get('name'), code=str(node.get('id'))) for node in graph.nodes]
        nodes = ClinicalDiseaseCategoryNode.objects.bulk_create(nodes)

        output = ''
        for i, data in enumerate(graph.nodes):
            index = str(data.get('id'))
            edges = data.get('edges')

            node = next((x for x in nodes if x.code == index), None)
            if not node:
                continue

            output = f'{output}\n\tNode<index: {i}, name: {node.name}, code: {node.code}> ['
            if len(edges) > 0:
                for j, element in enumerate(edges):
                    connection = next((x for x in nodes if x.code == str(element)), None)
                    if not connection:
                        continue
                    output = f'{output}\n\t\tConnection<index: {j}, name: {connection.name}, code: {connection.code}>'
                    node.add_child(connection)
                output = output + '\n\t]'
            else:
                output = output + ' ]'
        self.__log('Graph Generation<DebugGraph> {%s\n}' % output)

        if self._log_dir:
            self.__log_dots(nodes=nodes, name='DebugGraph')

    def add_arguments(self, parser):
        """
            Handles arguments given via the CLI

        """
        parser.add_argument('-p', '--print', type=bool, help='Print debug information to the terminal')
        parser.add_argument('-f', '--file', type=str, help='Location of DAG data relative to manage.py')
        parser.add_argument('-d', '--debug', type=bool, help='If true, attempts to generate DAG and ignores the --file parameter')
        parser.add_argument('-l', '--log', type=str, help=f'Expects directory, will output logs incl. DOTS representation to file as {self.LOG_FILE_NAME}{self.LOG_FILE_EXT}')

    @transaction.atomic
    def handle(self, *args, **kwargs):
        """
            Main command handle

        """
        # init parameters
        verbose = kwargs.get('print')
        filepath = kwargs.get('file')
        is_debug = kwargs.get('debug')
        log_file = kwargs.get('log')

        # det. handle
        self._verbose = verbose
        self._log_dir = log_file

        if is_debug:
            self.__generate_debug_dag()
        else:
            self.__try_build_dag(filepath or self.DEFAULT_FILE)
