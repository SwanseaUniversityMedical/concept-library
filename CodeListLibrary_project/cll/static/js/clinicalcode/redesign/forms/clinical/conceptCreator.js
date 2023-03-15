/**
 * ConceptCreator
 * @desc A class that can be used to control concept creation
 * 
 */
export default class ConceptCreator {
  constructor(data) {
    this.data = data || [ ];
  }

  getData() {
    return this.data;
  }
}
