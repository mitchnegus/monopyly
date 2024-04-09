/**
 * Facilitate the replacement of form values with suggestions.
 */


/**
 * A class for replacing elements of a form with suggested values.
 */
class SuggestionSelector {

  /**
   * Create the suggestion selector.
   *
   * @param {JQuery} $suggestion - An object that will have its text
   *     used to determine the value for replacement
   */
  constructor($suggestion) {
    this.$suggestion = $suggestion;
    const selector = this;
    this.$suggestion.on("click", function() {
      selector.#replaceValue();
    });
  }

  /**
   * Replace the value of the input field (by ID) with the suggested value.
   */
  #replaceValue() {
    const $formField = this.$suggestion.closest(".form-field.suggestable");
    const $input = $formField.find("input");
    $input.val(this.getSuggestionText());
  }

  /**
   * Get the text of the suggestion from the suggestion object.
   */
  getSuggestionText() {
    return this.$suggestion.text();
  }

}


/**
 * A class for replacing amount values on a form with suggested values.
 */
class AmountSuggestionSelector extends SuggestionSelector {

  /**
   * Get the text of the amount suggestion from the suggestion object.
   */
  getSuggestionText() {
    return this.$suggestion.text().replace("$", "").replace(",", "");
  }


}


export { SuggestionSelector, AmountSuggestionSelector };
