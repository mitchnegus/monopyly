/*
 * Add and remove subform fields to the current form.
 *
 * Opens an interface for adding and removing subform fields. The
 * interface allows a user to add a form field to an active form (via an
 * AJAX request) as well as providing a mechanism for removing the form
 * field.
 */

import { executeAjaxRequest } from "./ajax.js";

/**
 * A class for managing subforms (specifically dynamic form fields).
 */
class SubformManager {

  /**
   * Create the manager.
   *
   * @param {string} addFormEndpoint - The endpoint to reach when accessing the
   *     new subform info to be displayed.
   * @param {JQuery} $addFormButton - The button that adds a subform.
   * @param {JQuery} $removeFormButton - The button that removes a subform.
   */
  constructor(addFormEndpoint, $addFormButton, $removeFormButton) {
    this.addFormEndpoint = addFormEndpoint;
    this.$addFormButton = $addFormButton;
    this.$removeFormButton = $removeFormButton;
    // Bind actions to the buttons when clicked
    this.$addFormButton.on("click", this.#executeAjaxRequest.bind(this));
  }

  /**
   * Add the subform.
   */
  addSubform(response) {
    throw new Error("Define behavior to add the subform in a subclass.");
  }

  /**
   * Determine a data structure containing data to pass to the AJAX request.
   */
  determineAjaxData() {
    return null;
  }

  /**
   * Execute the AJAX request to retrieve the subform.
   */
  #executeAjaxRequest() {
    const rawData = this.determineAjaxData();
    const callback = this.addSubform.bind(this);
    executeAjaxRequest(this.addFormEndpoint, rawData, callback);
  }

}


export { SubformManager };

