/*
 * Provide autocomplete suggestions when filling out a transaction form.
 *
 * When entering a credit card transaction, provide autocomplete
 * suggestions to the  user. The suggestions are pulled from the
 * database for the field being input using an AJAX request. They are
 * ordered (on the server side) by their occurrence frequency and then
 * filtered here by the current input text after the input field is
 * changed.
 */

import { AutocompleteBox } from './modules/autocomplete_input.js';


(function() {

  setAutocomplete();

  function setAutocomplete() {
    let autocompleteBox;
    // Use a delegated event handler to use autocomplete
    $('form').on('focus', '.autocomplete input', function() {
      const inputElement = this;
      autocompleteBox = new AutocompleteBox(inputElement);
      // Identify the vendor input box (used when suggesting notes)
      const $vendor = $('form input#vendor');
      autocompleteAjaxRequest(autocompleteBox, inputElement, $vendor);
    });

    $('form').on('blur', '.autocomplete input', function() {
      autocompleteBox.release();
    });
  }

  function autocompleteAjaxRequest(autocompleteBox, inputElement, $vendor = null) {
    const inputID = inputElement.id.split('-');
    const field = inputID[inputID.length-1];
    const rawData = {
      'field': field,
      'vendor': $vendor.val()
    };
    // Use the AJAX request to finish setting up the autocomplete box
    autocompleteBox.ajaxRequest(AUTOCOMPLETE_ENDPOINT, rawData);
  }

})();

