'''
    ---------------------------------------------------------------------------
    Permissions

    For deciding who gets to access what.
    ---------------------------------------------------------------------------
'''
import json

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from dataclasses import replace


class Permissions:
    NONE = 1
    VIEW = 2
    EDIT = 3
    PERMISSION_CHOICES = ((NONE, 'No Access'), (VIEW, 'View'), (EDIT, 'Edit'))

    PERMISSION_CHOICES_WORLD_ACCESS = ((NONE, 'No Access'), (VIEW, 'View'))



def checkIfPublished(set_class, set_id, set_history_id):
    ''' Check if an entity version is published '''

    from .models.Concept import Concept
    from .models.Phenotype import Phenotype
    from .models.PhenotypeWorkingset import PhenotypeWorkingset
    from .models.PublishedConcept import PublishedConcept
    from .models.PublishedPhenotype import PublishedPhenotype
    from .models.PublishedWorkingset import PublishedWorkingset

    if (set_class == Concept):
        return PublishedConcept.objects.filter(concept_id=set_id, concept_history_id=set_history_id).exists()
    elif (set_class == Phenotype):
        return PublishedPhenotype.objects.filter(phenotype_id=set_id, phenotype_history_id=set_history_id, approval_status=2).exists()
    elif (set_class == PhenotypeWorkingset):
        return PublishedWorkingset.objects.filter(workingset_id=set_id, workingset_history_id=set_history_id, approval_status=2).exists()
    else:
        return False


def get_publish_approval_status(set_class, set_id, set_history_id):
    ''' Get the puublish approval status '''

    from .models.Concept import Concept
    from .models.Phenotype import Phenotype
    from .models.PhenotypeWorkingset import PhenotypeWorkingset
    from .models.PublishedConcept import PublishedConcept
    from .models.PublishedPhenotype import PublishedPhenotype
    from .models.PublishedWorkingset import PublishedWorkingset

    if (set_class == Phenotype):
        return PublishedPhenotype.objects.filter(phenotype_id = set_id, phenotype_history_id = set_history_id).values_list("approval_status", flat=True).first()
    elif (set_class == PhenotypeWorkingset):
        return PublishedWorkingset.objects.filter(workingset_id = set_id, workingset_history_id = set_history_id).values_list("approval_status", flat=True).first()

    # elif (set_class == Concept):
    #     return PublishedConcept.objects.filter(concept_id = set_id).values_list('approval_status', flat=True).first()
    
    else:
        return False


'''
    ---------------------------------------------------------------------------
    Determine access to a specified dataset (Concepts or WorkingSets).
    The allowed_to functions return a True/False result.
    The validate functions raise a PermissionDenied exception based on the
    allowed_to test.
    ---------------------------------------------------------------------------
'''


def allowed_to_view_children(request,
                            set_class,
                            set_id,
                            returnErrors=False,
                            WS_concepts_json="",
                            WS_concept_version=None,
                            set_history_id=None):
    '''
        Permit viewing access if:
        user is a super-user
        OR
        object is permitted to view 
            AND ALL children concepts are permitted to be viewed
    '''
    from .db_utils import (get_concept_versions_in_workingset,
                           get_history_child_concept_components,
                           getConceptsFromJSON, getConceptTreeByConceptId,
                           getGroupOfConceptsByPhenotypeId_historical,
                           getGroupOfConceptsByWorkingsetId_historical,
                           get_concept_data_of_historical_phenotypeWorkingset)
    from .models.Component import Component
    from .models.Concept import Concept
    from .models.Phenotype import Phenotype
    from .models.WorkingSet import WorkingSet
    from .models.PhenotypeWorkingset import PhenotypeWorkingset

    user = request.user
    errors = dict()
    if user.is_superuser:
        if returnErrors:
            return True, errors
        else:
            return True
    concepts = []
    permitted = False
    # The Working Set and Concept systems are fundamentally different, so we
    # need to check that here. Why?
    if (set_class == WorkingSet):
        permitted = allowed_to_view(request,
                                    WorkingSet,
                                    set_id,
                                    set_history_id=set_history_id)
        if (not permitted):
            errors[set_id] = 'Working set not permitted.'
        # Need to parse the concept_informations section of the database and use
        # the concepts here to form a list of concept_ref_ids.

        #         if WS_concepts_json.strip() != "":
        #             concepts =  getConceptsFromJSON(concepts_json = WS_concepts_json)
        #         else:
        #             concepts = getGroupOfConceptsByWorkingsetId_historical(set_id , set_history_id)
        if WS_concept_version is not None:
            concepts = WS_concept_version
        else:
            concepts = get_concept_versions_in_workingset(set_id, set_history_id)

        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add((int(concept), concepts[concept]))
        
    elif set_class == Phenotype:
        permitted = allowed_to_view(request, Phenotype, set_id)
        if (not permitted):
            errors[set_id] = 'Phenotype not permitted.'
            # Need to parse the concept_informations section of the database and use
            # the concepts here to form a list of concept_ref_ids.
        if WS_concepts_json:
            concepts = [(x['concept_id'], x['concept_version_id']) for x in WS_concepts_json]  
        else:
            concepts = getGroupOfConceptsByPhenotypeId_historical(set_id, set_history_id)

        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add(concept)
            
    elif set_class == PhenotypeWorkingset:
        permitted = allowed_to_view(request, PhenotypeWorkingset, set_id)
        if (not permitted):
            errors[set_id] = 'Working set not permitted.'
            # Need to parse the concept_informations section of the database and use
            # the concepts here to form a list of concept_ref_ids.
        if WS_concepts_json:
            concepts = [(int(x['concept_id'].replace('C', '')), x['concept_version_id'], x['phenotype_id'], x['phenotype_version_id']) for x in WS_concepts_json]  
        else:
            concepts = get_concept_data_of_historical_phenotypeWorkingset(set_id, set_history_id)

        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add(concept)
                
    elif (set_class == Concept):
        permitted = allowed_to_view(request,
                                    Concept,
                                    set_id,
                                    set_history_id=set_history_id)
        if (not permitted):
            errors[set_id] = 'Concept not permitted.'

        # Now, with no sync propagation, we check only one level for permissions
        concepts = get_history_child_concept_components(set_id, concept_history_id=set_history_id)
        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add((concept['concept_ref_id'], concept['concept_ref_history_id']))

    #         # Need to refer to all the components that have this id as its concept_id.
    #         # For each of these we need to create a list of concept ids from the
    #         # concept_ref_ids.
    #         # Basically, we need the ConceptTree table from concept_unique_codes(SQL).
    #         # At the moment we need to extract both the id and ref_id values from
    #         # what is a complete list but incomplete tree.
    #         concepts = getConceptTreeByConceptId(set_id)
    #         unique_concepts = set()
    #         for concept in concepts:
    #             unique_concepts.add(concept['concept_idx'])
    #             unique_concepts.add(concept['concept_ref_id'])
    else:
        pass
    # In both cases, we end up with a list of concept_ref_ids to which we need
    # view permission to all in order to grant permission.

    # Now check all the unique Concepts for access.
    permittedToAll = True
    for concept in unique_concepts:
        permitted = False
        if set_class == PhenotypeWorkingset:  # check access to phenotypes
            permitted = allowed_to_view(request,
                                        Phenotype,
                                        set_id=concept[2],
                                        set_history_id=concept[3])
            if (not permitted):
                errors[concept[2]] = 'Child phenotype not permitted.'
                permittedToAll = False
        else: # check access to concepts
            permitted = allowed_to_view(request,
                                        Concept, 
                                        set_id=concept[0],
                                        set_history_id=concept[1])

            if (not permitted):
                errors[concept[0]] = 'Child concept not permitted.'
                permittedToAll = False

    if returnErrors:
        return permittedToAll, errors
    else:
        return permittedToAll


def allowed_to_view(request,
                    set_class,
                    set_id,
                    set_history_id=None,
                    user=None):
    '''
        Permit viewing access if:
        user is a super-user or the OWNER
        OR
        viewing is permitted to EVERYONE
        OR
        viewing is permitted to a GROUP that contains the user
        
        if login_required is False this means it can be a published content
        --
        user will be read from request.user unless given directly via param: user
    '''

    if user is None and request is not None:
        user = request.user

    from .models.Concept import Concept
    from .models.Phenotype import Phenotype
    from .models.PhenotypeWorkingset import PhenotypeWorkingset

    # from .models.WorkingSet import WorkingSet
    # check if the entity/version exists
    if not set_class.objects.filter(id=set_id).exists():
        return False

    if set_history_id is not None:
        if not set_class.history.filter(id=set_id, history_id=set_history_id).exists():
            return False

    # Check if the user is permitted to view the entity
    # *** here check if the user can view  *******
    is_allowed_to_view = False

    is_authenticated = False
    if request is None:  # from unit-testing only
        is_authenticated = True
    else:
        is_authenticated = request.user.is_authenticated

    if is_authenticated:
        if user.is_superuser:
            is_allowed_to_view = True
        else:
            # if a specific version is published
            if set_history_id is not None and set_class in (Concept, Phenotype, PhenotypeWorkingset):
                if checkIfPublished(set_class, set_id, set_history_id):
                    is_allowed_to_view = True

            # Owner is always allowed to view
            if set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0:
                is_allowed_to_view = True
                
            if set_class.objects.filter(Q(id=set_id), Q(world_access=Permissions.VIEW)).count() > 0:
                is_allowed_to_view = True
                
            # this condition is not active now (from the interface), since not logical to give Edit permission to all users
            if set_class.objects.filter(Q(id=set_id), Q(world_access=Permissions.EDIT)).count() > 0:
                is_allowed_to_view = True
                
            for group in user.groups.all():
                if set_class.objects.filter(Q(id=set_id), Q(group_access=Permissions.VIEW, group_id=group)).count() > 0:
                    is_allowed_to_view = True
                if set_class.objects.filter(Q(id=set_id), Q(group_access=Permissions.EDIT, group_id=group)).count() > 0:
                    is_allowed_to_view = True
                
            # allow moderator to see pending/rejected phenotypes/concepts
            if is_member(user, "Moderators") and set_history_id is not None:
                approval_status = get_publish_approval_status(set_class, set_id, set_history_id)
                if approval_status in [1, 3]: # pending or rejected
                    is_allowed_to_view = True

    else:  # public content
        # check if the version is published
        if set_history_id is None:
            # get the latest version
            set_history_id = int(set_class.objects.get(pk=set_id).history.latest().history_id)

        is_published = checkIfPublished(set_class, set_id, set_history_id)

        if is_published:
            is_allowed_to_view = True
    # ********************************************

    # check brand access
    if is_allowed_to_view and request is not None:
        if not is_brand_accessible(request, set_class, set_id, set_history_id):
            is_allowed_to_view = False

    return is_allowed_to_view


def allowed_to_edit(request, set_class, set_id, user=None):
    '''
        Permit editing access if:
        user is a super-user or the OWNER
        OR
        editing is permitted to EVERYONE
        OR
        editing is permitted to a GROUP that the user belongs to
        but NOT if
        the application is configured as READ-ONLY.
        
        (skip this for now)(The object must not be marked as deleted - even for superuser)
        --
        user will be read from request.user unless given directly via param: user
    '''

    if user is None and request is not None:
        user = request.user

    if settings.CLL_READ_ONLY: return False

    # to_restore = False
    # skip this for now
    # skip this when restoring
    # if not to_restore:
    #   if set_class.objects.get(id=set_id).is_deleted==True: return False

    # *** here check if the user can edit  *******
    is_allowed_to_edit = False

    if user.is_superuser:
        is_allowed_to_edit = True
    else:
        if set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0:
            is_allowed_to_edit = True

        # this condition is not active now (from the interface), since not logical to give Edit permission to all users
        if set_class.objects.filter(Q(id=set_id), Q(world_access=Permissions.EDIT)).count() > 0:
            is_allowed_to_edit = True

        for group in user.groups.all():
            if set_class.objects.filter(Q(id=set_id), Q(group_access=Permissions.EDIT, group_id=group)).count() > 0:
                is_allowed_to_edit = True
    # ********************************************

    # check brand access
    if is_allowed_to_edit and request is not None:
        if not is_brand_accessible(request, set_class, set_id):
            is_allowed_to_edit = False

    return is_allowed_to_edit


def allowed_to_create():
    '''
        Permit creation unless we have a READ-ONLY application.
    '''
    if settings.CLL_READ_ONLY: return False
    return True


def allowed_to_permit(user, set_class, set_id):
    '''
        The ability to change the owner of a concept remains with the owner and
        not with those granted editing permission. And with superusers to get
        us out of trouble, when necessary.

        Allow user to change permissions if:
        user is a super-user
        OR
        user owns the object.
    '''
    if user.is_superuser: return True
    return set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0


def allowed_to_publish(user, set_class, set_id, historical_id):
    '''
        Allow to publish if:
        - Concept is not deleted
        - user is an owner
        - Concept contains codes
    '''
    from .db_utils import getGroupOfCodesByConceptId_HISTORICAL

    if (set_class.objects.get(id=set_id).is_deleted == True): return False

    if (set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0):
        return len(getGroupOfCodesByConceptId_HISTORICAL(concept_id=set_id, concept_history_id=historical_id)) > 0
    else:
        return False


def getGroups(user):
    '''
        if superuser, return all groups.
        else return groups where user is a member.
    '''
    if user.is_superuser:
        return Group.objects.all().exclude(name='ReadOnlyUsers')
    return user.groups.all().exclude(name='ReadOnlyUsers')


def validate_access_to_view(request, set_class, set_id, set_history_id=None):
    '''
        Validate if user has access to view the entity.
        Raises an exception if access is not allowed which causes the 403.html
        page to be displayed.
    '''
    if allowed_to_view(request, set_class, set_id, set_history_id=set_history_id) == False:
        raise PermissionDenied


def validate_access_to_edit(request, set_class, set_id):
    '''
        Validate if user has access to edit a dataset.
        Raises an exception if access is not allowed which causes the 403.html
        page to be displayed.
    '''

    if allowed_to_edit(request, set_class, set_id) == False:
        raise PermissionDenied


def validate_access_to_create():
    '''
        Validate if user has create permission.
        Raises an exception if access is not allowed which causes the 403.html
        page to be displayed.
    '''
    if allowed_to_create() == False:
        raise PermissionDenied


'''
    ---------------------------------------------------------------------------
    Mixin classes.
    ---------------------------------------------------------------------------
    !!! The Concept and Component Check Mixins are identical except for the
        ident of the selecting parameter. Fix this :)
'''


class HasAccessToCreateCheckMixin(object):
    '''
        mixin to check if user has create access for concepts
        this mixin is used within class based views and can be overridden
    '''

    def has_access_to_create(self, user):
        return allowed_to_create()

    def access_to_create_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_create(request.user):
            return self.access_to_create_failed(request, *args, **kwargs)

        return super(HasAccessToCreateCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToViewConceptCheckMixin(object):
    '''
        mixin to check if user has view access to a concept
        this mixin is used within class based views and can be overridden
    '''

    def has_access_to_view_concept(self, user, concept):
        from .models.Concept import Concept
        return allowed_to_view(self.request, Concept, concept)

    def access_to_view_concept_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_view_concept(request.user, self.kwargs['pk']):
            return self.access_to_view_concept_failed(request, *args, **kwargs)

        return super(HasAccessToViewConceptCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToViewParentConceptCheckMixin(object):
    '''
        mixin to check if user has view access to a component concept
        this mixin is used within class based views and can be overridden
    '''

    def has_access_to_view_concept(self, user, concept):
        from .models.Concept import Concept
        return allowed_to_view(self.request, Concept, concept)

    def access_to_view_concept_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_view_concept(request.user, self.kwargs['concept_id']):
            return self.access_to_view_concept_failed(request, *args, **kwargs)

        return super(HasAccessToViewParentConceptCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToEditConceptCheckMixin(object):
    '''
        mixin to check if user has edit access to a concept
        this mixin is used within class based views and can be overridden
    '''

    def has_access_to_edit_concept(self, user, concept):
        from .models.Concept import Concept
        return allowed_to_edit(self.request, Concept, concept)

    def access_to_edit_concept_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_edit_concept(request.user, self.kwargs['pk']):
            return self.access_to_edit_concept_failed(request, *args, **kwargs)

        return super(HasAccessToEditConceptCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToEditParentConceptCheckMixin(object):
    '''
        Mixin to check if user has edit access to a concept's parent concept.
        This differs from the Concept check only by the kwarg key used
        /concepts/<concept-id>/concepts/<pk>
    '''

    def has_access_to_edit_concept(self, user, concept):
        from .models.Concept import Concept
        return allowed_to_edit(self.request, Concept, concept)

    def access_to_edit_concept_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_edit_concept(request.user, self.kwargs['concept_id']):
            return self.access_to_edit_concept_failed(request, *args, **kwargs)

        return super(HasAccessToEditParentConceptCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToEditWorkingsetCheckMixin(object):
    '''
        mixin to check if user has edit access to a working set
        this mixin is used within class based views and can be overridden
    '''

    def has_access_to_edit_workingset(self, user, workingset_id):
        from .models.WorkingSet import WorkingSet
        return allowed_to_edit(self.request, WorkingSet, workingset_id)

    def access_to_edit_workingset_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_edit_workingset(request.user):
            return self.access_to_edit_workingset_failed(request, *args, **kwargs)

        return super(HasAccessToEditWorkingsetCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToViewWorkingsetCheckMixin(object):
    '''
        mixin to check if user has view access to a working set
        this mixin is used within class based views and can be overridden
    '''

    def has_access_to_view_workingset(self, user, workingset_id):
        from .models.WorkingSet import WorkingSet
        return allowed_to_view(self.request, WorkingSet, workingset_id)

    def access_to_view_workingset_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_view_workingset(request.user, self.kwargs['pk']):
            return self.access_to_view_workingset_failed(request, *args, **kwargs)

        return super(HasAccessToViewWorkingsetCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToEditPhenotypeCheckMixin(object):
    """
        mixin to check if user has edit access to a phenotype
        this mixin is used within class based views and can be overridden
    """

    def has_access_to_edit_phenotype(self, user, phenotype_id):
        from .models.Phenotype import Phenotype
        return allowed_to_edit(self.request, Phenotype, phenotype_id)

    def access_to_edit_phenotype_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_edit_phenotype(request.user):
            return self.access_to_edit_phenotype_failed(request, *args, **kwargs)

        return super(HasAccessToEditPhenotypeCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToViewPhenotypeCheckMixin(object):
    """
        mixin to check if user has view access to a phenotype
        this mixin is used within class based views and can be overridden
    """

    def has_access_to_view_phenotype(self, user, phenotype_id, phenotype_history_id):
        from .models.Phenotype import Phenotype
        return allowed_to_view(self.request, Phenotype, phenotype_id, set_history_id=phenotype_history_id)

    def access_to_view_phenotype_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_view_phenotype(request.user, self.kwargs['pk'], self.kwargs['phenotype_history_id']):
            return self.access_to_view_phenotype_failed(request, *args, **kwargs)

        return super(HasAccessToViewPhenotypeCheckMixin, self).dispatch(request, *args, **kwargs)


'''
    ---------------------------------------------------------------------------
    Produce permitted data-sets.
    ---------------------------------------------------------------------------
'''


def get_visible_codes(user, codeListID):
    '''
        Get the permitted codes.
        If no code list is specified, look through them all, adding codes that
        are contained in permitted code lists.
        If a code list is specified, just return the codes in that code list
        if it is permitted.
        (work only on live version since it is used in edit form)
    '''
    from .models.Code import Code
    codes = Code.objects.distinct()
    codelists = get_visible_codelists(user, codeListID)
    if user.is_superuser:
        if codeListID is not None:
            return codes.filter(Q(code_list=codeListID))
        else:
            return codes
    query = Code.objects.none()
    for codelist in codelists:
        query |= codes.filter(Q(code_list=codelist.id))
    return query


def get_visible_codelists(user, codeListID):
    '''
        Get the permitted codelists.
        Codelists do not carry permissions. Components are permitted by virtue
        of being part of a permitted concept. There is a one-to-one relation-
        ship between codelists and components.
        If we want all the permitted codelists, we need to find all the
        permitted components and add each component's codelist to the list.
        If we want to determine if codeListID is permitted, we just need to
        find the component that contains it.
        (work only on live version since it is used in edit form)
    '''
    from .models.CodeList import CodeList
    codelists = CodeList.objects.distinct()
    components = get_visible_components(user, codeListID)
    if user.is_superuser:
        if codeListID is not None:
            return codelists.filter(Q(id=codeListID))
        else:
            return codelists
    query = CodeList.objects.none()
    for component in components:
        if codeListID is not None:
            query = codelists.filter(Q(id=codeListID, component=component))
            return query
        else:
            query |= codelists.filter(Q(component=component))
    return query


def get_visible_components(user, codeListID):
    '''
        A component may be a Concept, CodeList or CodeRegex generated by a query-builder,
        expression or expression select.
        COMPONENT_TYPE_CONCEPT = 1
        COMPONENT_TYPE_QUERY_BUILDER = 2
        COMPONENT_TYPE_EXPRESSION = 3
        COMPONENT_TYPE_EXPRESSION_SELECT = 4
        (work only on live version since it is used in edit form)
    '''
    from .models.CodeList import CodeList
    from .models.Component import Component

    if user.is_superuser:
        if codeListID is not None:
            # Get the component ID for the codelist.
            codelist = CodeList.objects.get(id=codeListID)
            components = Component.objects.filter(id=codelist.component_id)
        else:
            components = Component.objects.distinct()
        return components

    if codeListID is not None:
        # Get the component ID for the codelist.
        codelist = CodeList.objects.get(id=codeListID)
        components = Component.objects.filter(id=codelist.component_id)
        concepts = get_visible_concepts_live(user).filter(id=components[0].concept_id)
    else:
        # Start with them all! (not enabled now - no use)
        components = Component.objects.distinct()
        concepts = get_visible_concepts_live(user)
    '''
        Not sure that the following is the right way to do it as it is not very
        scalable: trying to achieve visibility of a component only if the
        concept AND containing concept are visible.
    '''
    query = Component.objects.none()
    # count = 0
    for concept in concepts:
        '''
            Types 2,3 and 4 have a concept, but concept_ref is null. So add
            these only if the concept is in the list of visible concepts.
            Type 1 has a concept and concept_ref, so add this only if both
            concepts are visible.
        '''
        '''
            Use a union() rather than |= to combine the results so that we can
            remove duplicates with a distinct() call and thus reduce the amount
            of copying that happens. Empirically this has become unacceptable
            with a component list of 70 items.
        '''
        queryBuilders = Q(component_type=Component.COMPONENT_TYPE_QUERY_BUILDER, concept=concept.id)
        expressions = Q(component_type=Component.COMPONENT_TYPE_EXPRESSION, concept=concept.id)
        expressionSelects = Q(component_type=Component.COMPONENT_TYPE_EXPRESSION_SELECT, concept=concept.id)
        newQuery = components.filter(queryBuilders | expressions | expressionSelects)
        # Only add the query if it will add new components, otherwise we
        # needlessly quickly end up with a huge query.
        if newQuery.count() > 0:
            query = (query.union(newQuery)).distinct()
        # For this concept, include all referenced concepts which are also
        # visible.
        for conceptRef in concepts:
            if concept.id != conceptRef.id:
                otherConcepts = components.filter(Q(component_type=Component.COMPONENT_TYPE_CONCEPT, concept=concept.id, concept_ref=conceptRef.id))
                # Only add the query if it will add new components, otherwise we
                # needlessly quickly end up with a huge query.
                if otherConcepts.count() > 0:
                    query = (query.union(otherConcepts)).distinct()
    return query


def get_visible_concepts_live(user):
    ''' return visible live concepts'''
    # This does NOT excludes deleted ones
    from .models.Concept import Concept
    concepts = Concept.objects.distinct()
    if user.is_superuser: return concepts
    query = concepts.filter(Q(world_access=Permissions.VIEW))
    query |= concepts.filter(Q(world_access=Permissions.EDIT))
    query |= concepts.filter(Q(owner=user))
    for group in user.groups.all():
        query |= concepts.filter(
            Q(group_access=Permissions.VIEW, group_id=group))
        query |= concepts.filter(
            Q(group_access=Permissions.EDIT, group_id=group))

    return query


def get_visible_concepts_org(user,
                             get_Published_concepts=True,
                             show_concept_versions=False):
    # This does NOT excludes deleted ones
    from .models.Concept import Concept
    concepts = Concept.objects.distinct()
    if user.is_superuser: return concepts
    query = concepts.filter(Q(world_access=Permissions.VIEW))
    query |= concepts.filter(Q(world_access=Permissions.EDIT))
    query |= concepts.filter(Q(owner=user))
    for group in user.groups.all():
        query |= concepts.filter(Q(group_access=Permissions.VIEW, group_id=group))
        query |= concepts.filter(Q(group_access=Permissions.EDIT, group_id=group))

    return query


def get_visible_concepts(request,
                        get_Published_concepts=True,
                        show_concept_versions=False):
    # This does NOT excludes deleted ones
    from .db_utils import (get_list_of_visible_entity_ids, get_visible_live_or_published_concept_versions)
    from .models.Concept import Concept
    from .models.PublishedConcept import PublishedConcept

    user = request.user

    if not get_Published_concepts or PublishedConcept.objects.all().count() == 0:
        concepts = Concept.objects.distinct()

        if user.is_superuser:
            return concepts

        query = concepts.filter(Q(world_access=Permissions.VIEW))
        query |= concepts.filter(Q(world_access=Permissions.EDIT))
        query |= concepts.filter(Q(owner=user))
        for group in user.groups.all():
            query |= concepts.filter(Q(group_access=Permissions.VIEW, group_id=group))
            query |= concepts.filter(Q(group_access=Permissions.EDIT, group_id=group))

        return query

    else:
        history_ids_list = get_list_of_visible_entity_ids(get_visible_live_or_published_concept_versions(request, exclude_deleted=True),
                                                          return_id_or_history_id="history_id")
        return Concept.history.filter(history_id__in=history_ids_list)


def get_visible_workingsets(user):
    # This does NOT excludes deleted ones
    from .models.WorkingSet import WorkingSet
    workingsets = WorkingSet.objects.distinct()
    if user.is_superuser:
        return workingsets

    query = workingsets.filter(Q(world_access=Permissions.VIEW))
    query |= workingsets.filter(Q(world_access=Permissions.EDIT))
    query |= workingsets.filter(Q(owner=user))
    for group in user.groups.all():
        query |= workingsets.filter(Q(group_access=Permissions.VIEW, group_id=group))
        query |= workingsets.filter(Q(group_access=Permissions.EDIT, group_id=group))

    return query

def get_visible_phenotypes(user):
    # This does NOT excludes deleted ones
    from .models.Phenotype import Phenotype
    phenotypes = Phenotype.objects.distinct()

    if user.is_superuser:
        return phenotypes

    query = phenotypes.filter(Q(world_access=Permissions.VIEW))
    query |= phenotypes.filter(Q(world_access=Permissions.EDIT))
    query |= phenotypes.filter(Q(owner=user))

    for group in user.groups.all():
        query |= phenotypes.filter(Q(group_access=Permissions.VIEW, group_id=group))
        query |= phenotypes.filter(Q(group_access=Permissions.EDIT, group_id=group))

    return query


def get_visible_data_sources(user):
    # This does NOT excludes deleted ones
    from .models.DataSource import DataSource
    datasources = DataSource.objects.distinct()

    if user.is_superuser:
        return datasources

    query = datasources.filter(Q(world_access=Permissions.VIEW))
    query |= datasources.filter(Q(world_access=Permissions.EDIT))
    query |= datasources.filter(Q(owner=user))

    for group in user.groups.all():
        query |= datasources.filter(Q(group_access=Permissions.VIEW, group_id=group))
        query |= datasources.filter(Q(group_access=Permissions.EDIT, group_id=group))

    return query


def is_member(user, group_name):
    return user.groups.filter(name__iexact=group_name).exists()


def is_brand_accessible(request, set_class, set_id, set_history_id=None):
    """
        When in a brand, show only this brand's data
    """
    from .db_utils import get_brand_collection_ids, getHistoryTags_Workingset
    from .models.Concept import Concept
    from .models.Phenotype import Phenotype
    from .models.WorkingSet import WorkingSet
    from .models.PhenotypeWorkingset import PhenotypeWorkingset

    # setting set_history_id = None,
    # so this permission is always checked from the live obj like other permissions
    set_history_id = None

    brand = request.CURRENT_BRAND
    if brand == "":
        return True
    else:
        brand_collection_ids = get_brand_collection_ids(brand)

        if not brand_collection_ids:
            return True

        if brand_collection_ids:
            history_id = set_history_id
            if set_history_id is None:
                history_id = set_class.objects.get(pk=set_id).history.latest().history_id

            set_collections = []
            if set_class in (Concept, Phenotype):
                set_collections = set_class.history.get(id=set_id, history_id=history_id).tags

            elif set_class == PhenotypeWorkingset:
                set_collections = set_class.history.get(id=set_id, history_id=history_id).collections
                
            elif set_class == WorkingSet:
                workingset_history_date = set_class.history.get(id=set_id, history_id=history_id).history_date
                ws_tags = getHistoryTags_Workingset(set_id, workingset_history_date)
                if ws_tags:
                    set_collections = [i['tag_id'] for i in ws_tags if 'tag_id' in i]

            if not set_collections:
                return False
            else:
                # check if the set collections has any of the brand's collection tags
                return any(c in set_collections for c in brand_collection_ids)

            
            
