/*
 * Add a bank transfer option to a bank transaction form.
 *
 * Adds fields to the transaction form to allow the transaction to be
 * recorded as a transfer taking place jointly between accounts. When
 * the button is pressed to record a transfer, an AJAX request is
 * executed to retrieve an extra set of subfields for the transaction
 * form. The page is updated with the new field information.
 */

import { SubformManager } from './modules/manage_subforms.js';


/**
 * A class for managing bank transfer subforms.
 */
class BankTransferSubformManager extends SubformManager {

  /**
   * Create the manager.
   */
  constructor() {
    // Identify the button to add subfields for recording transfers
    const $button = $('#new-transfer.button');
    super(ADD_TRANSFER_FORM_ENDPOINT, $button, true);
  }

  /**
   * Add the subform.
   */
  addSubform(response) {
    $('.add-info.buttons').after(response);
  }

}

(function() {

  const subformManager = new BankTransferSubformManager();

})();

