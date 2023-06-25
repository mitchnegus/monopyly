/*
 * Provide autocomplete suggestions when filling out a transaction form.
 *
 * When entering a transaction, provide autocomplete suggestions to the user.
 * The suggestions are pulled from the database for the field being input
 * using an AJAX request. They are ordered (on the server side) by their
 * occurrence frequency and then filtered here by the current input text after
 * the input field is changed.
 */

import { AutocompleteBox } from './modules/autocomplete-input.js';


(function() {

  setAutocomplete();

  function setAutocomplete() {
    let autocompleteBox;
    // Use a delegated event handler to use autocomplete
    $('form').on('focus', '.autocomplete input', function() {
      const inputElement = this;
      const inputName = $(inputElement).attr("name");
      if (inputName.endsWith("tags")) {
        autocompleteBox = new TagAutocompleteBox(inputElement);
      } else {
        autocompleteBox = new AutocompleteBox(inputElement);
      }
      // Identify the merchant input box (used when suggesting notes)
      const $merchant = $('form input#merchant');
      autocompleteAjaxRequest(autocompleteBox, inputElement, $merchant);
    });

    $('form').on('blur', '.autocomplete input', function() {
      autocompleteBox.release();
    });
  }

  function autocompleteAjaxRequest(autocompleteBox, inputElement, $merchant = null) {
    const inputID = inputElement.id.split('-');
    const field = inputID[inputID.length-1];
    const rawData = {
      'field': field,
      'merchant': $merchant.val()
    };
    // Use the AJAX request to finish setting up the autocomplete box
    autocompleteBox.ajaxRequest(AUTOCOMPLETE_ENDPOINT, rawData);
  }

})();


/**
 * A class for performing autocomplete on tags inputs.
 */
class TagAutocompleteBox extends AutocompleteBox {

  /**
   * Create the autcomplete box for tags.
   */
  constructor(inputElement) {
    super(inputElement);
  }

  /**
   * Populate the last tag in the input element using the chosen suggestion.
   */
  fill(suggestion) {
    const lastTagName = suggestion.textContent;
    const tagArray = this.#separateTags(this.inputElement.value);
    // Pad the added tag with a space (if it is not the first/only element)
    let padding;
    if (tagArray.length == 1) {
      padding = "";
    } else {
      padding = " ";
    }
    tagArray[tagArray.length-1] = padding + lastTagName;
    this.inputElement.value = tagArray.join(",");
  }

  /**
   * Refesh autocomplete suggestions using only the last input tag.
   */
  refreshMatches(userInput) {
    const autocompleteSegment = this.#separateTags(userInput).pop().trim();
    super.refreshMatches(autocompleteSegment);
  }

  #separateTags(userInput) {
    return userInput.split(",");
  }

}
