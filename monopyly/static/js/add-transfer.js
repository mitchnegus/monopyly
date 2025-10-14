/*
 * Add a bank transfer option to a bank transaction form.
 *
 * Adds fields to the transaction form to allow the transaction to be
 * recorded as a transfer taking place jointly between accounts. When
 * the button is pressed to record a transfer, an AJAX request is
 * executed to retrieve an extra set of subfields for the transaction
 * form. The page is updated with the new field information.
 */

import { SubformManager } from './modules/manage-subforms.js';


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
    // Ensure that the subform is only added once
    const $subform = $('div#transfer_accounts_info-0.subform');
    if (!$subform.length) {
      $('.add-info.buttons').after(response);
      // Disable the merchant field (it is replaced by the linked bank name)
      $('input#merchant').val("");
      $('input#merchant').prop("disabled", true);
    }
  }

  /**
   * Remove the subform
   */
  removeSubform($subform) {
    $subform.remove();
    // Reenable the merchant field
    $('input#merchant').prop("disabled", false);
  }

}

(function() {

  const subformManager = new BankTransferSubformManager();

})();

