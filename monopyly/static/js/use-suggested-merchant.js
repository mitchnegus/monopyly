/* Replace credit transaction form merchant field value with a suggestion.
 */

import { SuggestionSelector } from 'dry-foundation/form-suggestions';


(function() {

  const $suggestion = $(".merchant-suggestion .merchant");
  new SuggestionSelector($suggestion);

})();
