/* Replace the value in the transaction form subtotal field with a suggestion.
 */

(function() {

  const $suggestion = $(".amount-suggestion .currency");
  const suggestedAmount = $suggestion.text().replace("$", "").replace(",", "");
  const $inputAmount = $suggestion.closest(".subform").find("input.currency");
  $suggestion.on("click", function() {
    $inputAmount.val(suggestedAmount);
  });

})();
