'''
    Unit Tests for Permissions

    For deciding who gets to access what.
'''

from django.test import TestCase


class SmokeTest(TestCase):

    @classmethod
    def setUp(self):
        print("Permissions tests ...")

    '''def test_bad_maths(self):
        self.assertEqual(1 + 1, 3)'''


"""
'''
    Permissions code follows:-
'''
from django.db.models import Q
from django.core.exceptions import PermissionDenied

class Permissions:
    OWNER = 1
    EVERYONE = 2
    GROUP = 3
    PERMISSION_CHOICES = (
        (OWNER, 'OWNER'),
        (EVERYONE, 'EVERYONE'),
        (GROUP, 'GROUP')
    )
    
'''
    ---------------------------------------------------------------------------
    ACCESS TO DATASETS (CONCEPTS AND WORKING-SETS)
    ---------------------------------------------------------------------------
'''
def allowed_to_view(user, set_class, set_id):
    '''
        Permit viewing access if:
        user is a super-user
        OR
        concept viewing is permitted to EVERYONE
        OR
        concept viewing is permitted to the OWNER who is the user
        OR
        concept viewing is permitted to a GROUP that contains the user
    '''
    #if user.is_superuser: return True
    permitted = False
    #query = set_class.objects.filter(Q(concept_id=set_id), Q(shared=Permissions.EVERYONE))
    permitted |= set_class.objects.filter(Q(concept_id=set_id), Q(shared=Permissions.EVERYONE)).count() > 0
    #query = set_class.objects.filter(Q(concept_id=set_id), Q(shared=Permissions.OWNER, owned_by=user))
    permitted |= set_class.objects.filter(Q(concept_id=set_id), Q(shared=Permissions.OWNER, owned_by=user)).count() > 0
    for group in user.groups.all() :
        #query = set_class.objects.filter(Q(concept_id=set_id), Q(shared=Permissions.GROUP, group_id=group))
        permitted |= set_class.objects.filter(Q(concept_id=set_id), Q(shared=Permissions.GROUP, group_id=group)).count() > 0
        
    return permitted

def allowed_to_edit(user, set_class, set_id):
    '''
        Permit editing access if:
        user is a super-user
        OR
        concept editing is permitted to EVERYONE
        OR
        concept editing is permitted to the OWNER who is the user
        OR
        concept editing is permitted to a GROUP that the user belongs to
    '''
    #if user.is_superuser: return True
    permitted = False
    #query = set_class.objects.filter(Q(concept_id=set_id), Q(editable=Permissions.EVERYONE))
    permitted |= set_class.objects.filter(Q(concept_id=set_id), Q(editable=Permissions.EVERYONE)).count() > 0
    #query = set_class.objects.filter(Q(concept_id=set_id), Q(editable=Permissions.OWNER, owned_by=user))
    permitted |= set_class.objects.filter(Q(concept_id=set_id), Q(editable=Permissions.OWNER, owned_by=user)).count() > 0
    for group in user.groups.all() :
        #query = set_class.objects.filter(Q(concept_id=set_id), Q(editable=Permissions.GROUP, group_id=group))
        permitted |= set_class.objects.filter(Q(concept_id=set_id), Q(editable=Permissions.GROUP, group_id=group)).count() > 0
        
    return permitted
'''
    ---------------------------------------------------------------------------
    ACCESS TO CONCEPTS AND CONCEPT FEATURES
    ---------------------------------------------------------------------------
'''
def get_visible_concepts(user):
    from .models.Concept import Concept
    concepts = Concept.objects.distinct()
    if user.is_superuser: return concepts
    query = concepts.filter(Q(shared=Permissions.EVERYONE))
    query |= concepts.filter(Q(shared=Permissions.OWNER, owned_by=user))
    for group in user.groups.all() :
        query |= concepts.filter(Q(shared=Permissions.GROUP, group_id=group))
    return query

    ''' Pta: An alternative version which we might want to use for editable as well.
    concept = Concept.objects.get(pk=concept_id)
    if concept.is_deleted == True:
        messages.info(self.request, "Concept has been deleted.")

    return db_utils.has_access_to_view_concept(self.kwargs['pk'], user)
    '''
def can_change_concept_owner(user, concept_id):
    '''
        The ability to change the owner of a concept remains with the owner and
        not with those granted editing permission. And with superusers to get
        us out of trouble, when necessary.
    '''
    from .models.Concept import Concept
    if user.is_superuser: return True
    return Concept.objects.filter(Q(concept_id=concept_id), Q(owned_by=user)).count > 0
    
def validate_access_to_view_concept(user, concept_id):
    ''' validate if user has access to view a concept '''
    from .models.Concept import Concept
    if allowed_to_view(user, Concept, concept_id) == False:
        raise PermissionDenied
    
def validate_access_to_edit_concept(user, concept_id):
    ''' validate if user has access to edit a concept '''
    from .models.Concept import Concept
    if allowed_to_edit(user, Concept, concept_id) == False:
        raise PermissionDenied

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


'''
    ---------------------------------------------------------------------------
    ACCESS TO WORKING-SETS AND WORKING-SET FEATURES
    ---------------------------------------------------------------------------
'''
def validate_access_to_view_workingset(user, workingset_id):
    ''' validate if user has access to view a concept '''
    from .models.WorkingSet import WorkingSet
    if allowed_to_view(user, WorkingSet, workingset_id) == False:
        raise PermissionDenied

def validate_access_to_edit_workingset(user, workingset_id):
    ''' validate if user has access to edit a concept '''
    from .models.WorkingSet import WorkingSet
    if allowed_to_edit(user, WorkingSet, workingset_id) == False:
        raise PermissionDenied
"""
