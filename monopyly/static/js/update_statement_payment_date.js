/* * Update a credit card statement's payment date.
 *
 * When a user clicks the 'Pay this statement' button on the statement
 * details page, this script presents the input box allowing them to
 * enter a payment date. The button (after a neat CSS effect) is
 * converted into a submit button and can be used to submit the payment
 * date. The submit button completes an AJAX request to mark the statement
 * as paid. If the date is given in an acceptable format, the database is
 * updated. Otherwise, if the form loses focus before the submit button is
 * pushed, the payment form is returned to its initial state.
 */

// Identify the key elements
let $buttonPay = $('#make-payment[type="button"]');
let $inputPayDate = $('#pay-date');

// Allow dates to be entered into the form
bindButtonChange();

// Clicking outside the form returns the form to its original state
$(document).on('click', function(event) {
	let $formPay = $('form#pay');
	// Change the button type back to 'button' for clicks outside the form
	if (!$formPay.is(event.target) && $formPay.has(event.target).length === 0) {
		$buttonPay[0].type = 'button';
		bindButtonChange();
	}
});

function bindButtonChange() {
	$buttonPay.on('click', function(event) {
		// Change the button type to 'submit'
		this.type = 'submit';
		// Stop the form from being submitted
		event.preventDefault();
		// Submit the form if the button is clicked again
		$buttonPay.off('click');
		$inputPayDate.select();
	});
}
