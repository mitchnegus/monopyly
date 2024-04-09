/* Replace credit transaction form merchant field value with a suggestion.
 */
import { SuggestionSelector } from './modules/form-suggestions.js';


(function() {

  const $suggestion = $(".merchant-suggestion .merchant");
  new SuggestionSelector($suggestion);

})();
