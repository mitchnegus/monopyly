/*
 * Make a payment on a credit card statement.
 *
 * When a user clicks the 'Make a payment' button on the statement
 * details page, this script presents the input box allowing them to
 * enter a payment amount and date. The button (after a neat CSS effect)
 * is converted into a submit button and can be used to submit the
 * payment information. The submit button completes an AJAX request to
 * mark the statement as paid. If the amount and date are given in an
 * acceptable format, the database is updated. Otherwise, if the form
 * loses focus before the submit button is pushed, the payment form is
 * returned to its initial state.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  const $summaryContainer = $('#statement-summary-container');
  const $transactionContainer = $('#statement-transactions-container');
  prepareForm();

  function prepareForm() {

    // Identify the key elements
    let $buttonPay = $('#make-payment[type="button"]');

    if ($buttonPay.length) {
      let $inputPayAmount = $('#pay-amount');
      let $inputPayDate = $('#pay-date');
      let $selectPayBankAccount = $('#pay-bank-account');
      // Change the form to allow information to be entered/submitted
      bindButtonChange(
        $buttonPay,
        $inputPayAmount,
        $inputPayDate,
        $selectPayBankAccount
      );
      // Clicking outside the form returns the form to its original state
      $(document).on('click', function(event) {
        const $formPay = $('form#pay');
        // Change the button type back to 'button' for clicks outside the form
        if (!$formPay.is(event.target) && $formPay.has(event.target).length === 0) {
          $buttonPay.off('click');
          $buttonPay[0].type = 'button';
          bindButtonChange(
            $buttonPay,
            $inputPayAmount,
            $inputPayDate,
            $selectPayBankAccount
          );
        }
      });
    }
  }

  function bindButtonChange($buttonPay, $inputPayAmount, $inputPayDate,
                            $selectPayBankAccount) {
    $buttonPay.on('click', function(event) {
      // Change the button type to 'submit'
      this.type = 'submit';
      // Stop the form from being submitted
      event.preventDefault();
      // Submit the form if the button is clicked again
      $buttonPay.off('click');
      $buttonPay.on('click', function(event) {
        // Stop the form from being submitted by the form action
        event.preventDefault();
        // Submit the form using an AJAX request
        const rawData = {
          'payment_amount': $inputPayAmount.val(),
          'payment_date': $inputPayDate.val(),
          'payment_bank_account': $selectPayBankAccount.val()
        }
        updateStatementPaymentAjaxRequest(rawData);
      });
      $inputPayAmount.select();
    });
  }


  function updateStatementPaymentAjaxRequest(rawData) {
    // Return the newly updated statement payment info
    function updateAction(response) {
      $summaryContainer.html(response[0]);
      $transactionContainer.html(response[1]);
      // Prepare the form again (in case statement is not paid in full)
      prepareForm();
    }
    executeAjaxRequest(MAKE_PAYMENT_ENDPOINT, rawData, updateAction);
  }

})();
