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
   * @param {boolean} toggleButton - ...
   */
  constructor(addFormEndpoint, $addFormButton, toggleButton=false) {
    this.addFormEndpoint = addFormEndpoint;
    this.$addFormButton = $addFormButton;
    this.toggleButton = toggleButton;
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
    const callback = this.#handleAjaxResponse.bind(this);
    executeAjaxRequest(this.addFormEndpoint, rawData, callback);
  }

  /**
   * Remove the subform
   */
  removeSubform($subform) {
    $subform.remove();
  }

  /**
   * Provide an AJAX callback that adds a subform and binds the remove button.
   */
  #handleAjaxResponse(response) {
    this.addSubform(response);
    if (this.toggleButton) {
      this.$addFormButton.hide();
    }

    const $removeButtons = $(".subform .close.button");
    const manager = this;
    $removeButtons.on("click", function() {
      manager.removeSubform(this.closest(".subform"));
      if (manager.toggleButton) {
        manager.$addFormButton.show();
      }
    });
  }

}


export { SubformManager };

