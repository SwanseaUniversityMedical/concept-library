from ..clinicalcode import ClinicalCode

def clinicalcode(request):
    return {'clinicalcode': ClinicalCode(request)}
