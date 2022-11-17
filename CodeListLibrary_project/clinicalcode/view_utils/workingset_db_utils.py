def deletePhenotypeWorkingset(pk, user):
    ''' Delete a phenotypeworkingset based on a workingset id '''
    # get selected workingset
    workingset = PhenotypeWorkingset.objects.get(pk=pk)
    workingset.is_deleted = True
    workingset.deleted = datetime.datetime.now()
    workingset.deleted_by = user
    workingset.changeReason = standardiseChangeReason("Deleted")
    workingset.save()


def restorePhenotypeWorkingset(pk, user):
    ''' Restore a phenotypeworkingset '''
    # get selected workingset
    workingset = PhenotypeWorkingset.objects.get(pk=pk)
    workingset.is_deleted = False
    workingset.deleted = None
    workingset.deleted_by = None
    workingset.updated_by = user
    workingset.changeReason = standardiseChangeReason("restored")
    workingset.save()


def validate_phenotype_workingset_attribute(attribute):
    """ Attempts to parse the given attribute's value as it's given datatype

        Returns:
            1. boolean
                -> describes success state
            2. any[value, string]
                -> returns value as the proposed datatype if successful
                -> returns a description of the error if failure occurs
    """
    from clinicalcode.constants import PWS_ATTRIBUTE_TYPE_DATATYPE

    proposed_type = attribute['type']
    proposed_value = attribute['value']

    if proposed_type in PWS_ATTRIBUTE_TYPE_DATATYPE:
        expected_type = PWS_ATTRIBUTE_TYPE_DATATYPE[proposed_type]
        try:
            value = expected_type(proposed_value)
            return True, value
        except:
            return False, f"Attribute error: '{proposed_value}' could not be parsed as type '{proposed_type}', expected {expected_type}"

    is_case_issue = proposed_type.upper() in PWS_ATTRIBUTE_TYPE_DATATYPE
    issue = f"Attribute error: Unknown type '{proposed_type}'"
    if is_case_issue:
        issue += f". Did you mean '{proposed_type.upper()}'?"

    return False, issue