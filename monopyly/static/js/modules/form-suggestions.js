/**
 * Facilitate the replacement of form values with suggestions.
 */

import { SuggestionSelector } from 'dry-foundation/form-suggestions';


/**
 * A class for replacing amount values on a form with suggested values.
 */
class AmountSuggestionSelector extends SuggestionSelector {

  /**
   * Get the text of the amount suggestion from the suggestion object.
   */
  getSuggestionText() {
    return this.$suggestion.text().replace(/[$,]/g, "").trim();
  }


}


export { AmountSuggestionSelector };
