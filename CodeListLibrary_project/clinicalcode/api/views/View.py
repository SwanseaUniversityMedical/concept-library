"""
    ---------------------------------------------------------------------------
    API VIEW
    API access to the data to list the various data types (if access is
    permitted) and to access the data structure and components of groups of
    data types.
    ---------------------------------------------------------------------------
"""
from functools import wraps
from django.conf import settings


def get_canonical_path(request, force_HDRUK_rel=False):
    # refer HDRUK branded pages to phenotypes.healthdatagateway.org 
    CANONICAL_PATH = request.build_absolute_uri(request.path)
    cp = CANONICAL_PATH
    if (settings.IS_HDRUK_EXT == '0' and settings.CURRENT_BRAND == 'HDRUK') or force_HDRUK_rel:
        url_list = CANONICAL_PATH.split('/')
        if len(url_list) > 4:
            start_index = 4
            if url_list[3].upper() == 'HDRUK':
                start_index = 4
            else:
                start_index = 3
            cp = 'https://phenotypes.healthdatagateway.org/' + '/'.join(url_list[start_index:])
        else:
            cp = 'https://phenotypes.healthdatagateway.org' 
 
    # manage protocol
    if settings.IS_DEVELOPMENT_PC or settings.IS_INSIDE_GATEWAY:
        cp = cp.replace("https://", "http://" , 1)
    else:
        cp = cp.replace("http://", "https://" , 1)
    return cp


def get_canonical_path_by_brand(request,
                              set_class,
                              pk,
                              history_id):

    """
        [!] This is LEGACY - We no longer have Concept / Phenotype pages
            - This needs to be updated if it's truly required to utilise the GenericEntity model
        
        Legacy description:
            "if a concept/phenotype belongs to HDRUK and opened in default site
            set canonical link to phenotypes.healthdatagateway.org"

    """
    # if set_class == Concept:
    #     ver = getHistoryConcept(history_id)
    # elif set_class == Phenotype:
    #     ver = getHistoryPhenotype(history_id)
    # else:
    #     return get_canonical_path(request)

    # if ver['tags'] is None:
    #     return get_canonical_path(request)
        
    # set_collections = Tag.objects.filter(id__in=ver['tags'], tag_type=2)
    
    # # check if any collection is related to HDRUK
    # HDRUK_collections =  get_brand_associated_collections(request
    #                                                     , concept_or_phenotype = ['phenotype', 'concept'][set_class == Concept]
    #                                                     , brand = 'HDRUK'
    #                                                     )
    
    # if any(c in set_collections for c in HDRUK_collections):
    #     return get_canonical_path(request, force_HDRUK_rel=True)
    # else:
    #     return get_canonical_path(request)
    return get_canonical_path(request)
    

def robots(content="all"):
    """
        not to index demo site API
        and add the canonical link
    """
    def _method_wrapper(func):
        @wraps(func)
        def wrap(request, *args, **kwargs):
            response = func(request, *args, **kwargs)

            if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC or settings.IS_HDRUK_EXT == "0":
                content="noindex, nofollow"
                response['X-Robots-Tag'] = content

            response['Link'] = get_canonical_path(request) + '; rel="canonical"'
            return response

        return wrap
    return _method_wrapper


def robots2(content="all"):
    """
        not to index demo site API
        and add the canonical link after checking the brand
    """
    def _method_wrapper(func):
        @wraps(func)
        def wrap(request, *args, **kwargs):
            response = func(request, *args, **kwargs)
            
            if settings.IS_DEMO or settings.IS_DEVELOPMENT_PC or settings.IS_HDRUK_EXT == "0":
                content="noindex, nofollow"
                response['X-Robots-Tag'] = content
                
            response['Link'] = get_canonical_path(request) + '; rel="canonical"'
            if 'pk' in kwargs and 'set_class' in kwargs and 'is_authenticated_user' in kwargs:  
                if not kwargs['is_authenticated_user']:
                    if kwargs['pk'] is not None:
                        history_id = None
                        if 'history_id' in kwargs:
                            history_id = kwargs['history_id']
                            
                        if history_id is None:
                            # get the latest version
                            history_id = kwargs['set_class'].objects.get(pk=kwargs['pk']).history.latest().history_id
                            
                        response['Link'] = get_canonical_path_by_brand(request,
                                                                      set_class = kwargs['set_class'],
                                                                      pk = kwargs['pk'],
                                                                      history_id = history_id
                                                                      )

            return response
        return wrap
    return _method_wrapper
