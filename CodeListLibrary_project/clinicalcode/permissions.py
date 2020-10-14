'''
    ---------------------------------------------------------------------------
    Permissions

    For deciding who gets to access what.
    ---------------------------------------------------------------------------
'''
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib.auth.models import User, Group

class Permissions:
    NONE = 1
    VIEW = 2
    EDIT = 3
    PERMISSION_CHOICES = (
        (NONE, 'No Access'),
        (VIEW, 'View'),
        (EDIT, 'Edit')
    )
    
    PERMISSION_CHOICES_WORLD_ACCESS = (
        (NONE, 'No Access'),
        (VIEW, 'View')
    )

'''
    ---------------------------------------------------------------------------
    Determine access to a specified dataset (Concepts or WorkingSets).
    The allowed_to functions return a True/False result.
    The validate functions raise a PermissionDenied exception based on the
    allowed_to test.
    ---------------------------------------------------------------------------
'''
def allowed_to_view_children(user, set_class, set_id, returnErrors = False, WS_concepts_json = "", set_history_id = None):
    '''
        Permit viewing access if:
        user is a super-user
        OR
        concept is permitted to view 
            AND ALL children concepts are permitted to be viewed
    '''
    from .models.Concept import Concept
    from .models.WorkingSet import WorkingSet
    from .models.Component import Component
    
    from db_utils import (getConceptTreeByConceptId, getGroupOfConceptsByWorkingsetId
                          , getConceptsFromJSON, getGroupOfConceptsByWorkingsetId_historical
                          , get_history_child_concept_components
                          )
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
        permitted = allowed_to_view(user, WorkingSet, set_id)
        if (not permitted):
            errors[set_id] = 'Working set not permitted.'
        # Need to parse the concept_informations section of the database and use
        # the concepts here to form a list of concept_ref_ids.
        
        if WS_concepts_json.strip() != "":
            concepts =  getConceptsFromJSON(concepts_json = WS_concepts_json)
        else:
            if set_history_id is None:
                concepts = getGroupOfConceptsByWorkingsetId(set_id)
            else:
                concepts = getGroupOfConceptsByWorkingsetId_historical(set_id , set_history_id)
        
        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add(int(concept))
        pass
    elif (set_class == Concept):
        permitted = allowed_to_view(user, Concept, set_id)
        if (not permitted):
            errors[set_id] = 'Concept not permitted.'
        
        # Now, with no sync propagation, we check only one level for permissions
        concepts = get_history_child_concept_components(set_id, concept_history_id=set_history_id)
        unique_concepts = set()
        for concept in concepts:
            unique_concepts.add(concept['concept_ref_id'])
            
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
        permitted |= Concept.objects.filter(Q(id=concept), Q(world_access=Permissions.VIEW)).count() > 0
        permitted |= Concept.objects.filter(Q(id=concept), Q(world_access=Permissions.EDIT)).count() > 0
        permitted |= Concept.objects.filter(Q(id=concept), Q(owner_access=Permissions.VIEW, owner=user)).count() > 0
        permitted |= Concept.objects.filter(Q(id=concept), Q(owner_access=Permissions.EDIT, owner=user)).count() > 0
        for group in user.groups.all() :
            permitted |= Concept.objects.filter(Q(id=concept), Q(group_access=Permissions.VIEW, group_id=group)).count() > 0
            permitted |= Concept.objects.filter(Q(id=concept), Q(group_access=Permissions.EDIT, group_id=group)).count() > 0
        if (not permitted):
            errors[concept] = 'Child concept not permitted.'             
            permittedToAll = False
                    
            
    if returnErrors:
        return permittedToAll, errors
    else:
        return permittedToAll


def allowed_to_view(user, set_class, set_id):
    '''
        Permit viewing access if:
        user is a super-user or the OWNER
        OR
        concept viewing is permitted to EVERYONE
        OR
        concept viewing is permitted to a GROUP that contains the user
    '''
    # Check if the user is permitted to view the concept - once permission is
    # granted for any reason return immediately.
    if user.is_superuser: return True
    # Owner is always allowed to view.
    if set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0: return True
    if set_class.objects.filter(Q(id=set_id), Q(world_access=Permissions.VIEW)).count() > 0: return True
    if set_class.objects.filter(Q(id=set_id), Q(world_access=Permissions.EDIT)).count() > 0: return True
    for group in user.groups.all() :
        if  set_class.objects.filter(Q(id=set_id), Q(group_access=Permissions.VIEW, group_id=group)).count() > 0: return True
        if  set_class.objects.filter(Q(id=set_id), Q(group_access=Permissions.EDIT, group_id=group)).count() > 0: return True      
    return False

def allowed_to_edit(user, set_class, set_id, to_restore=False):
    '''
        Permit editing access if:
        user is a super-user or the OWNER
        OR
        concept editing is permitted to EVERYONE
        OR
        concept editing is permitted to a GROUP that the user belongs to
        but NOT if
        the application is configured as READ-ONLY.
        (skip this for now)(The object must not be marked as deleted - even for superuser)
    '''
    if settings.CLL_READ_ONLY: return False
  
    # skip this for now
    # skip this when restoring 
    #if not to_restore:
    #   if set_class.objects.get(id=set_id).is_deleted==True: return False

    if user.is_superuser: return True
    

    if set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0: return True

    if set_class.objects.filter(Q(id=set_id), Q(world_access=Permissions.EDIT)).count() > 0: return True
    
    for group in user.groups.all() :
        if set_class.objects.filter(Q(id=set_id), Q(group_access=Permissions.EDIT, group_id=group)).count() > 0: return True
    return False

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
    from db_utils import getGroupOfCodesByConceptId_HISTORICAL 

    if(set_class.objects.get(id=set_id).is_deleted == True): return False
    
    if(set_class.objects.filter(Q(id=set_id), Q(owner=user)).count() > 0):
        return len(getGroupOfCodesByConceptId_HISTORICAL(concept_id=set_id, concept_history_id=historical_id)) > 0
    else:
        return False


def getGroups(user):
    '''
        if superuser, return all groups.
        else return groups where user is a member.
    '''
    if user.is_superuser: return Group.objects.all().exclude(name='ReadOnlyUsers')
    return user.groups.all().exclude(name='ReadOnlyUsers')
    
    
def validate_access_to_view(user, set_class, set_id):
    '''
        Validate if user has access to view a dataset.
        Raises an exception if access is not allowed which causes the 403.html
        page to be displayed.
    '''
    if allowed_to_view(user, set_class, set_id) == False:
        raise PermissionDenied


def validate_access_to_edit(user, set_class, set_id):
    '''
        Validate if user has access to edit a dataset.
        Raises an exception if access is not allowed which causes the 403.html
        page to be displayed.
    '''
    if allowed_to_edit(user, set_class, set_id) == False:
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
    

class HasAccessToPublishCheckMixin(object):
    '''
        mixin to check if user has publish access for concepts
        this mixin is used within class based views and can be overridden
    '''
    
    def has_access_to_publish(self, user, pk):
        from .models import Concept
        return allowed_to_permit(user, Concept, pk)

    def access_to_publish_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_publish(request.user, self.kwargs['pk']):
            return self.access_to_publish_failed(request, *args, **kwargs)

        return super(HasAccessToPublishCheckMixin, self).dispatch(request, *args, **kwargs)


class HasAccessToViewConceptCheckMixin(object):
    '''
        mixin to check if user has view access to a concept
        this mixin is used within class based views and can be overridden
    '''
    def has_access_to_view_concept(self, user, concept):
        from .models.Concept import Concept
        return allowed_to_view(user, Concept, concept)

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
        return allowed_to_view(user, Concept, concept)

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
        return allowed_to_edit(user, Concept, concept)

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
        return allowed_to_edit(user, Concept, concept)

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
        return allowed_to_edit(user, WorkingSet, workingset_id)

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
        return allowed_to_view(user, WorkingSet, workingset_id)

    def access_to_view_workingset_failed(self, request, *args, **kwargs):
        raise PermissionDenied

    def dispatch(self, request, *args, **kwargs):
        if not self.has_access_to_view_workingset(request.user, self.kwargs['pk']):
            return self.access_to_view_workingset_failed(request, *args, **kwargs)

        return super(HasAccessToViewWorkingsetCheckMixin, self).dispatch(request, *args, **kwargs)


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
        concepts = get_visible_concepts(user, get_Published_concepts=False).filter(id=components[0].concept_id)
    else:
        # Start with them all! (not enabled now - no use)
        components = Component.objects.distinct()
        concepts = get_visible_concepts(user, get_Published_concepts=False)
        
    '''
        Not sure that the following is the right way to do it as it is not very
        scalable: trying to achieve visibility of a component only if the
        concept AND containing concept are visible.
    '''
    query = Component.objects.none()
    #count = 0
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
                otherConcepts = components.filter(
                                    Q(component_type=Component.COMPONENT_TYPE_CONCEPT,
                                      concept=concept.id, concept_ref=conceptRef.id))
                # Only add the query if it will add new components, otherwise we
                # needlessly quickly end up with a huge query.
                if otherConcepts.count() > 0:
                    query = (query.union(otherConcepts)).distinct()
    return query


def get_visible_concepts(user, get_Published_concepts=True, show_concept_versions=False):
    # This does NOT excludes deleted ones
    from .models.Concept import Concept
    concepts = Concept.objects.distinct()
    if user.is_superuser: return concepts
    query = concepts.filter(Q(world_access=Permissions.VIEW))
    query |= concepts.filter(Q(world_access=Permissions.EDIT))
    query |= concepts.filter(Q(owner=user))
    for group in user.groups.all() :
        query |= concepts.filter(Q(group_access=Permissions.VIEW, group_id=group))
        query |= concepts.filter(Q(group_access=Permissions.EDIT, group_id=group))
    
    return query

    
        
def get_visible_conceptsXX(user, get_Published_concepts=True, show_concept_versions=False):
    # This does NOT excludes deleted ones
    from .models.Concept import Concept
    from .models.PublishedConcept import PublishedConcept
    from db_utils import *
    
    concepts = Concept.objects.distinct()
    
    if user.is_superuser: 
        return concepts #maybe add published ones as well
    
    visibleConcepts = concepts.filter(Q(world_access=Permissions.VIEW))
    visibleConcepts |= concepts.filter(Q(world_access=Permissions.EDIT))
    visibleConcepts |= concepts.filter(Q(owner=user))
    for group in user.groups.all() :
        visibleConcepts |= concepts.filter(Q(group_access=Permissions.VIEW, group_id=group))
        visibleConcepts |= concepts.filter(Q(group_access=Permissions.EDIT, group_id=group))
    
    visibleConcepts_ids = []

    #  Run through the concepts and add a 'can edit this concept' field, etc.
    for concept in visibleConcepts:
        concept.is_latest_ver = True
        latest_ver = None
        latest_ver = Concept.objects.get(pk=concept.id).history.latest()
        concept.history_id = latest_ver.history_id
        visibleConcepts_ids.append(concept.history_id)
        concept.is_published = checkIfPublished(concept.id, concept.history_id)
        if concept.is_published:
            concept.publish_date = PublishedConcept.objects.get(concept_id=concept.id, concept_history_id=concept.history_id).created
        else:
            concept.publish_date = None
        concept.can_edit = allowed_to_edit(user, Concept, concept.id)
        concept.history_date = latest_ver.history_date
        concept.history_change_reason = latest_ver.history_change_reason
        concept.history_type = latest_ver.history_type
        concept.history_user_id = latest_ver.history_user_id
            
    if not get_Published_concepts:
        return visibleConcepts
    #-------------------------------
    # add published concepts
    # work on concept.history and make sure it is in published concept
    all_published_history_id = list(PublishedConcept.objects.all().values_list('concept_history_id', flat=True))
    # removes the ones already added before
    
    published_concepts = Concept.history.filter(history_id__in = list(set(all_published_history_id) - set(visibleConcepts_ids))
                                                )
    if published_concepts.count() == 0:
        return visibleConcepts
    
    # removes the ones already added before
    ###published_concepts = published_concepts.all().exclude(history_id__in = visibleConcepts.values_list('history_id', flat=True))
    
    #  Run through the concepts and add a 'can edit this concept' field, etc.
    for concept in published_concepts:
        concept.is_latest_ver = False
        #concept.history_id  is here already
        concept.is_published = True
        concept.publish_date = PublishedConcept.objects.get(concept_id=concept.id, concept_history_id=concept.history_id).created
        concept.can_edit = False
        
    return (visibleConcepts | published_concepts.defer('history_id', 'history_date', 'history_change_reason', 'history_type', 'history_user_id')
            ).distinct()

#     # This does NOT excludes deleted ones
#     from .models.Concept import Concept
#     from .models.PublishedConceptVersions import PublishedConceptVersions
#     from db_utils import getAllConceptHistoryEntryies
#     
#     h= PublishedConceptVersions.objects.all()
#     
#     from django.db import models
#     z = model.objects.raw(...)
#     
#     if  get_Published_concepts:
#         concepts = Concept.objects.distinct()
#     else:
#         concepts = getAllConceptHistoryEntryies()
#         
#     if user.is_superuser: 
#         return concepts
#     
#     query = concepts.filter(Q(world_access=Permissions.VIEW))
#     query |= concepts.filter(Q(world_access=Permissions.EDIT))
#     query |= concepts.filter(Q(owner=user))
#     for group in user.groups.all() :
#         query |= concepts.filter(Q(group_access=Permissions.VIEW, group_id=group))
#         query |= concepts.filter(Q(group_access=Permissions.EDIT, group_id=group))        
#     
#     return query
#         
        
        
def get_visible_workingsets(user):
    # This does NOT excludes deleted ones
    from .models.WorkingSet import WorkingSet
    workingsets = WorkingSet.objects.distinct()
    if user.is_superuser: 
        return workingsets
    
    query = workingsets.filter(Q(world_access=Permissions.VIEW))
    query |= workingsets.filter(Q(world_access=Permissions.EDIT))
    query |= workingsets.filter(Q(owner=user))
    for group in user.groups.all() :
        query |= workingsets.filter(Q(group_access=Permissions.VIEW, group_id=group))
        query |= workingsets.filter(Q(group_access=Permissions.EDIT, group_id=group))
        
    return query

def is_member(user, group_name):
    return user.groups.filter(name=group_name).exists()

