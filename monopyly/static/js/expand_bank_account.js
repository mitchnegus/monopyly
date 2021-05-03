/*
 * Expand a bank account (on the 'Bank Accounts' page).
 *
 * Expands a bank account row in the bank account grouping for a given
 * bank when the row is clicked. The expanded row shows the options
 * menu for going to the bank's summary or deleting the account. A user
 * can exit the expanded view by clicking the 'x' icon button that is
 * shown in the expanded view.
 */

(function() {

  // Identify the account rows
  const $accountRow = $('#bank-container .account-block');
  // Set timing variables
  const slideTime = 250;

  $accountRow.on('click', function() {
    // Show the expanded transaction summary
    const $expandedRow = $(this).find('.expanded');
    $expandedRow.slideToggle(slideTime);
});

})();
