export const
  /**
   * CLU_DASH_TARGETS
   * @desc Describes `data-value` modifier(s)
   * 
   */
  CLU_LABELS = {
    pages: {
      // Views
      'inventory': 'Inventory',
      'brand-config': 'Brand Config',

      // Models
      'users': 'Users',
      'organisations': 'Organisations',
    }
  },
  /**
   * CLU_ACTIVITY_CARDS
   * @desc render information relating to activity statistics card(s)
   * 
   */
  CLU_ACTIVITY_CARDS = [
    {
      key: 'dau',
      name: 'DAU',
      desc: 'No. of unique Daily Active Users today.',
      icon: '&#xe473;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'mau',
      name: 'MAU',
      desc: 'No. of unique Monthly Active Users this month.',
      icon: '&#xf2a1;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'hits',
      name: 'Page Hits',
      desc: 'No. of page hits in the last 7 days.',
      icon: '&#xf06e;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'created',
      name: '${brandMapping.phenotype}s Created',
      desc: 'No. of ${brandMapping.phenotype}s created in the last 7 days',
      icon: '&#xf234;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'edited',
      name: '${brandMapping.phenotype}s Edited',
      desc: 'No. of ${brandMapping.phenotype}s edited in the last 7 days',
      icon: '&#xf4ff;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'published',
      name: '${brandMapping.phenotype}s Published',
      desc: 'No. of ${brandMapping.phenotype}s published in the last 7 days',
      icon: '&#xf02d;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'phenoflow',
      name: 'Phenoflow Associations',
      desc: '% of ${brandMapping.phenotype}s associated with Phenoflow',
      icon: '&#xf6ff;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'datasources',
      name: 'Data Source Use',
      desc: 'No. unique HDRUK Data Sources associated with ${brandMapping.phenotype}s',
      icon: '&#xf1c0;',
      iconCls: 'as-icon--warning',
    },
  ],
  /**
   * CLU_DASH_TARGETS
   * @desc Describes `data-value` modifier(s)
   * 
   */
  CLU_DASH_TARGETS = {
    NEXT: 'next',
    PREVIOUS: 'previous',
  },
  /**
   * CLU_DASH_ATTRS
   * @desc Field attr lookup
   * 
   */
  CLU_DASH_ATTRS = {
    username: {
      inputType: 'text',
      autocomplete: 'username',
    },
    first_name: {
      inputType: 'text',
      autocomplete: 'given-name',
    },
    last_name: {
      inputType: 'text',
      autocomplete: 'family-name',
    },
  },
  /**
   * CLU_DATATYPE_ATTR
   * @desc Field data attr lookup
   * 
   */
  CLU_DATATYPE_ATTR = {
    TimeField: 'time',
    DateField: 'date',
    DateTimeField: 'datetime-local',
  };
