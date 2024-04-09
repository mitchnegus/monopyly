/* Replace transaction form subtotal field value with a suggestion.
 */
import { AmountSuggestionSelector } from './modules/form-suggestions.js';


(function() {

  const $suggestion = $(".amount-suggestion .currency");
  new AmountSuggestionSelector($suggestion);

})();
