/*
 * Add a new subtransaction to a transaction form.
 *
 * Adds fields to the transaction form to allow the addition of a new
 * subtransaction. When the button is pressed to add a subtransaction,
 * a POST request is executed to retrieve an extra set of subfields for
 * the transaction form. The POST request includes information about the
 * the number of current subtransactions already being displayed, so
 * that new subtransaction fields may be indexed accordingly. The page
 * is updated with the new field information.
 */

import { SubformManager } from './modules/manage-subforms.js';


/**
 * A class for managing subtransaction subforms.
 */
class SubtransactionSubformManager extends SubformManager {

  /**
   * Create the manager.
   */
  constructor() {
    // Identify the button to add subtransaction entry forms
    const $button = $('#new-subtransaction.button');
    super(ADD_SUBTRANSACTION_FORM_ENDPOINT, $button);
  }

  /**
   * Add the subform at the end of the set of existing subtransaction forms.
   */
  addSubform(response) {
    $('#subtransactions').append(response);
  }

  /**
   * Create a raw data object containing the count of existing subtransactions.
   */
  determineRequestData() {
    const subtransactionCount = $('.subtransaction-form').length;
    const rawData = {'subtransaction_count': subtransactionCount};
    return rawData;
  }

}

(function() {

  const subformManager = new SubtransactionSubformManager();

})();
