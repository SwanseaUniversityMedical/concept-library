from django.core.management.base import BaseCommand
from django.db import transaction, connection

import re
import os
import json
import enum
import time

from .constants import GraphType, LogType
from ...entity_utils import constants
from ...models.CodingSystem import CodingSystem
from ...models.OntologyTag import OntologyTagEdge, OntologyTag
from ...generators.graphs.generator import Graph as GraphGenerator


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

            Note:

                ICD-10 codes were scraped from the ICD-10 classification website,
                and matched with the Atlas phecodes

                This builder generates a DAG of ICD-10 codes, matched with the codes
                within our database and selects the appropriate CodingSystem

        """

        ''' [!] Warning: This is only partially optimised '''
        if not isinstance(data, list):
            return False, 'Invalid data type, expected list but got %s' % type(data)

        # const
        icd_10_id = CodingSystem.objects.get(name='ICD10 codes').id

        # process nodes
        nodes = [ ]
        result = [ ]
        linkage = [ ]
        name_hashmap = { }
        started = time.time()

        def create_linkage(parent, parent_index, children):
            for child_data in children:
                name = child_data.get('name').strip()
                name = re.sub(r'\((\b(?=[a-zA-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*-\b(?=[A-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*)\)', '', name).strip()
                code = child_data.get('code').strip()

                # ICD-10 uses non-unique names, add code to vary them if required
                if name in name_hashmap:
                    name = f'{name} ({code})'
                name_hashmap[name] = True

                # Create child node and process descendants
                properties = { 'code': code, 'coding_system_id': icd_10_id }

                node = OntologyTag(name=name, type_id=constants.ONTOLOGY_TYPES.CLINICAL_DISEASE, properties=properties)
                index = len(nodes)
                nodes.append(node)
                linkage.append([parent_index, index])

                descendants = child_data.get('children')
                child_count = len(descendants) if isinstance(descendants, list) else 0
                result.append(f'\t\tChildDiseaseNode<name: {node.name}, code: {code}, children: {child_count}>')

                if isinstance(descendants, list):
                    create_linkage(node, index, descendants)

        for root_data in data:
            # clean up the section name(s) from scraped data
            root_name = root_data.get('name').strip()
            matched_code = re.search(r'(\b(?=[a-zA-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*-\b(?=[A-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*)', root_name)

            root_name = re.sub(r'\((\b(?=[a-zA-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*-\b(?=[A-Z\d]+)[a-zA-Z]*\d[a-zA-Z\d]*)\)', '', root_name).strip()
            derived_code = matched_code.group() if matched_code else None

            # process node and its branches
            properties = { 'code': derived_code, 'coding_system_id': icd_10_id }

            root = OntologyTag(name=root_name, type_id=constants.ONTOLOGY_TYPES.CLINICAL_DISEASE, properties=properties)
            index = len(nodes)
            nodes.append(root)

            children = root_data.get('sections')
            result.append(f'\tRootDiseaseNode<name: {root.name}, code: {derived_code}, children: {len(children)}>')

            create_linkage(root, index, children)

        with transaction.atomic():
            # bulk create nodes & children
            nodes = OntologyTag.objects.bulk_create(nodes)

            # bulk create edges
            OntologyTag.children.through.objects.bulk_create(
                [
                    # list comprehension here is required because we need to match the instance(s)
                    OntologyTag.children.through(
                        name=f'{nodes[link[0]].name} | {nodes[link[1]].name}',
                        parent=nodes[link[0]],
                        child=nodes[link[1]]
                    )
                    for link in linkage
                ],
                batch_size=7000
            )

        # update coding system and apply related code
        with connection.cursor() as cursor:
            ''' [!] Note: We could probably optimise this? '''

            sql = """
            -- update matched values
            update public.clinicalcode_ontologytag as trg
               set properties = properties || jsonb_build_object('code_id', src.code_id)
              from (
                select node.id as node_id,
                       code.id as code_id
                  from public.clinicalcode_ontologytag as node
                  join public.clinicalcode_icd10_codes_and_titles_and_metadata as code
                    on replace(node.properties->>'code'::text, '.', '') = replace(code.code, '.', '')
                 where node.properties is not null
                   and node.properties ? 'code'
                   and node.type_id = %(type_id)s
              ) src
             where trg.id = src.node_id
               and trg.type_id = %(type_id)s
               and trg.properties is not null;
            """
            cursor.execute(sql, { 'type_id': constants.ONTOLOGY_TYPES.CLINICAL_DISEASE.value })

        # create result string for log
        elapsed = (time.time() - started)
        result = 'Created DiseaseNodes<coding_system: %d, elapsed: %.2f s> {\n%s\n}' % (icd_10_id, elapsed, '\n'.join(result))

        return True, result

    @classmethod
    def ANATOMICAL_CATEGORIES(cls, data):
        """
            Anatomical category builder

            Note:

                Currently, there are no known links between anatomical categories
                provided by the Atlas dataset.

                As such, this method creates a tree without any children.

        """

        if not isinstance(data, list):
            return False, 'Invalid data type, expected list but got %s' % type(data)

        # process nodes
        nodes = [ ]
        result = [ ]
        started = time.time()

        for root_node in data:
            node_id = root_node.get('id')
            node_name = root_node.get('name')

            if not isinstance(node_id, int) or not isinstance(node_name, str):
                err = 'Failed to create Node, expected <id: number, name: string> but got Node<id: %s, name: %s>' \
                    % (type(node_id), type(node_name))
                return False, err

            node = OntologyTag(name=node_name.strip(), reference_id=node_id, type_id=constants.ONTOLOGY_TYPES.CLINICAL_FUNCTIONAL_ANATOMY)
            nodes.append(node)
            result.append(f'\tAnatomicalRootNode<name: {node_name}, id: {node_id}>')

        # bulk create nodes
        with transaction.atomic():
            nodes = OntologyTag.objects.bulk_create(nodes)

        # create result string for log
        elapsed = (time.time() - started)
        result = 'Created AnatomicalNodes<elapsed: %.2f s, count: %d> {\n%s\n}' % (elapsed, len(nodes), '\n'.join(result))

        return True, result

    @classmethod
    def SPECIALITY_CATEGORIES(cls, data):
        """
            Clinical domain builder

            Note:

                This speciality data was scraped from the Atlas datasources,
                it creates a tree hierarchy of clinical specialities and subspecialities

                DAG required as there are some specialities with overlap, e.g.:
                    
                    - Pre-hospital Emergency Medicine as as child of Anaesthetics, ICM and EM
                    - Paediatric Intensive Care Medicine as a child of Paediatrics and ICM

        """

        if not isinstance(data, dict):
            return False, 'Invalid data type, expected list but got %s' % type(data)

        # process nodes
        nodes = [ ]
        result = [ ]
        linkage = [ ]
        started = time.time()

        for root_key, children in data.items():
            root_name = root_key.strip()
            root_node = OntologyTag(name=root_name, type_id=constants.ONTOLOGY_TYPES.CLINICAL_DOMAIN)

            root_index = len(nodes)
            nodes.append(root_node)
            result.append(f'\tSpecialityRootNode<name: {root_name}>')

            if len(children) > 0:
                for child_key in children:
                    child_name = child_key.strip()

                    related_index = next((i for i, e in enumerate(nodes) if e.name == child_name), None)
                    if related_index is None:
                        related_index = len(nodes)
                        child = OntologyTag(name=child_name, type_id=constants.ONTOLOGY_TYPES.CLINICAL_DOMAIN)
                        nodes.append(child)

                    linkage.append([root_index, related_index])
                    result.append(f'\t\tChildSpecialityNode<name: {child_name}>')

        # bulk create nodes & children
        with transaction.atomic():
            nodes = OntologyTag.objects.bulk_create(nodes)

            # bulk create edges
            OntologyTag.children.through.objects.bulk_create(
                [
                    # list comprehension here is required because we need to match the instance(s)
                    OntologyTag.children.through(
                        name=f'{nodes[link[0]].name} | {nodes[link[1]].name}',
                        parent=nodes[link[0]],
                        child=nodes[link[1]]
                    )
                    for link in linkage
                ],
                batch_size=7000
            )

        # create result string for log
        elapsed = (time.time() - started)
        result = 'Created SpecialityNodes<elapsed: %.2f s> {\n%s\n}' % (elapsed, '\n'.join(result))

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
            self.__log_to_file(result, LogType.SUCCESS)

    def __generate_debug_dag(self):
        """
            Responsible for generating a debug dag using the graph generators & its utility methods

        """
        graph = GraphGenerator.generate(graph_type=GraphGenerator.Types.DirectedAcyclicGraph)
        nodes = [
            OntologyTag(
                name=node.get('name'),
                type_id=constants.ONTOLOGY_TYPES.CLINICAL_DISEASE,
                properties={'code': str(node.get('id')), 'coding_system_id': 4}
            )
            for node in graph.nodes
        ]
        nodes = OntologyTag.objects.bulk_create(nodes)

        output = ''
        for i, data in enumerate(graph.nodes):
            index = str(data.get('id'))
            edges = data.get('edges')

            node = next((x for x in nodes if x.code == index), None)
            if not node:
                continue

            output = f'{output}\n\tNode<index: {i}, name: {node.name}, code: {node.properties.get("code")}> ['
            if len(edges) > 0:
                for j, element in enumerate(edges):
                    connection = next((x for x in nodes if x.properties.get('code') == str(element)), None)
                    if not connection:
                        continue
                    output = f'{output}\n\t\tConnection<index: {j}, name: {connection.name}, code: {connection.properties.get("code")}>'
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
        self._log_dir = log_file if isinstance(log_file, str) and len(log_file) > 0 else None

        if is_debug:
            self.__generate_debug_dag()
        else:
            self.__try_build_dag(filepath or self.DEFAULT_FILE)
