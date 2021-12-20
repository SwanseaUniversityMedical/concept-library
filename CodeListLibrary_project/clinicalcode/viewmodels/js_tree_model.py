class TreeModelManager:
    def get_children(self):
        return self.children

    def build_child_tree(self, tree, parent, nodes):
        self.build_child_tree_recursive(tree, parent, nodes)

    def get_logical_name(self, logical_type):
        if logical_type == 1:
            return "Inclusion"
        elif logical_type == 2:
            return "Exclusion"
        else:
            return ""

    def build_child_tree_recursive(self, tree, parent, nodes):
        # find children
        children = [n for n in nodes if n['concept_idx'] == int(parent)]

        count = 0

        # build a subtree for each child
        for child in children:
            # start a new sub tree
            tree['children'].append({
                'text':
                child['component_name'] + ' - (Logical type: ' +
                self.get_logical_name(child['logical_type']) + ')',
                'id':
                child['concept_ref_id'],
                'state': {
                    'opened': True
                },
                'children': []
            })
            # call recursively to build a subtree for current node
            self.build_child_tree_recursive(tree['children'][count],
                                            child['concept_ref_id'], nodes)
            count += 1

    def build_parent_tree(self, tree, parent, nodes):
        self.build_parent_tree_recursive(tree, parent, nodes)

    def build_parent_tree_recursive(self, tree, parent, nodes):
        # find children
        children = [n for n in nodes if n['concept_id'] == int(parent)]

        count = 0

        # build a subtree for each child
        for child in children:
            # start a new sub tree
            tree['children'].append({
                'text':
                child['concept_name'] + ' - (' + child['component_name'] +
                ')' + ' - (Logical type: ' +
                self.get_logical_name(child['logical_type']) + ')',
                'id':
                child['concept_id'],
                'state': {
                    'opened': True
                },
                'children': []
            })
            # call recursively to build a subtree for current node
            self.build_parent_tree_recursive(tree['children'][count],
                                             child['concept_ref_id'], nodes)
            count += 1
