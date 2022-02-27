/*
 * Add a bank transfer option to a bank transaction form.
 *
 * Adds fields to the transaction form to allow the transaction to be
 * recorded as a transfer taking place jointly between accounts. When
 * the button is pressed to record a transfer, an AJAX request is
 * executed to retrieve an extra set of subfields for the transaction
 * form. The page is updated with the new field information.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  const endpoint = ADD_TRANSFER_FORM_ENDPOINT;
  // Identify the button to add subfields for recording transfers
  const $button = $('#new-transfer.button');

  $button.on('click', function() {
    // Execute the AJAX request to retrieve the transfer form
    function addTransferForm(response) {
      $('.add-info.buttons').after(response);
      $('#new-transfer').hide();
    }
    // Add the new transfer form to the bank transaction form
    executeAjaxRequest(endpoint, 0, addTransferForm);
  });

})();

