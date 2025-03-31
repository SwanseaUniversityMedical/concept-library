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
      name: 'Phenotypes Created',
      desc: 'No. of Phenotypes created in the last 7 days',
      icon: '&#xf234;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'edited',
      name: 'Phenotypes Edited',
      desc: 'No. of Phenotypes edited in the last 7 days',
      icon: '&#xf4ff;',
      iconCls: 'as-icon--warning',
    },
    {
      key: 'published',
      name: 'Phenotypes Published',
      desc: 'No. of Phenotypes published in the last 7 days',
      icon: '&#xf02d;',
      iconCls: 'as-icon--warning',
    },
  ],
  /**
   * CLU_DASH_KEYCODES
   * @desc Describes keycodes for dashboard related events
   * 
   */
  CLU_DASH_KEYCODES = {
    ENTER: 13,
  },
  /**
   * CLU_DASH_TARGETS
   * @desc Describes `data-value` modifier(s)
   * 
   */
  CLU_DASH_TARGETS = {
    NEXT: 'next',
    PREVIOUS: 'previous',
  };
