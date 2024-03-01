export const
  // Describes endpoints used to resolve data
  ENDPOINTS = {
    FETCH_NODE: '${host}/api/v1/ontology/node/${id}',
    FETCH_DATA: '${host}/api/v1/ontology/detail/${source}',
  },
  // Optional arguments to modify ontology service behaviour
  OPTIONS = {
    // i.e. modal-related options
    modalTitle: 'Select Ontology',
    modalSize: 'xl',
    modalConfirm: 'Confirm',
    modalCancel: 'Cancel',
  },
  /// Dialogue event response(s)
  EVENT_STATES = {
    // When a dialogue is cancelled without changes
    CANCELLED: 0,
  
    // When a dialogue is confirmed, with or without changes
    CONFIRMED: 1,
  }
