
# Component types
LOGICAL_TYPE_INCLUSION = 1
LOGICAL_TYPE_EXCLUSION = 2

LOGICAL_TYPES = (
    (LOGICAL_TYPE_INCLUSION, 'Add codes'),
    (LOGICAL_TYPE_EXCLUSION, 'Remove codes'),
)
    

# Regex types    
REGEX_TYPE_SIMPLE = 1
REGEX_TYPE_POSIX = 2

REGEX_TYPE_CHOICES = ((REGEX_TYPE_SIMPLE, 'simple (% only)'),
                      (REGEX_TYPE_POSIX, 'POSIX regex'))


# Publish approval
APPROVAL_REQUESTED = 0
PENDING = 1
APPROVED = 2
REJECTED = 3
APPROVED_STATUS = ((APPROVAL_REQUESTED, 'Requested'), 
                   (PENDING, 'Pending'),
                   (APPROVED, 'Approved'), 
                   (REJECTED, 'Rejected'))
    
    
Disease = 0
Biomarker = 1
Drug = 2
Lifestyle_risk_factor = 3
Musculoskeletal = 4
Surgical_procedure = 5
Type_status = ((Disease, 'Disease or syndrome '),
               (Biomarker,'Biomarker'),(Drug,'Drug'),
               (Lifestyle_risk_factor,'Lifestyle risk factor'),
               (Musculoskeletal,'Musculoskeletal'),
               (Surgical_procedure,'Surgical procedure'))