/**
 * PublicationCreator
 * @desc A class that can be used to control publication lists
 * 
 */
export default class PublicationCreator {
  constructor(data) {
    this.data = data || [ ];
  }

  getData() {
    return this.data;
  }
}
