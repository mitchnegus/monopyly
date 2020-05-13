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

(function() {

	// Identify the key elements
	const $container = $('#statement-info-container');
	let $buttonPay = $('#make-payment[type="button"]');
	let $inputPayAmount = $('#pay-amount');
	let $inputPayDate = $('#pay-date');
	
	// Allow dates to be entered into the form
	bindButtonChange($buttonPay, $inputPayAmount, $inputPayDate);
	
	// Clicking outside the form returns the form to its original state
	$(document).on('click', function(event) {
		const $formPay = $('form#pay');
		// Change the button type back to 'button' for clicks outside the form
		if (!$formPay.is(event.target) && $formPay.has(event.target).length === 0) {
			$buttonPay.off('click');
			$buttonPay[0].type = 'button';
			bindButtonChange($buttonPay, $inputPayAmount, $inputPayDate);
		}
	});
	
	function bindButtonChange($buttonPay, $inputPayAmount, $inputPayDate) {
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
					'payment_date': $inputPayDate.val()
				}
				updateStatementPaymentAjaxRequest(rawData);
			});
			$inputPayAmount.select();
		});
	}
	
	function updateStatementPaymentAjaxRequest(rawData) {
		// Return the newly updated statement payment info
		$.ajax({
			url: MAKE_PAYMENT_ENDPOINT,
			type: 'POST',
			data: JSON.stringify(rawData),
			contentType: 'application/json; charset=UTF-8',
			success: function(response) {
				$container.html(response)
				// Bind the buttons/inputs again
				$buttonPay = $('#make-payment[type="button"]');
				$inputPayAmount = $('#pay-amount');
				$inputPayDate = $('#pay-date');
		 		bindButtonChange($buttonPay, $inputPayAmount, $inputPayDate);
			},
			error: function(xhr) {
				console.log('There was an error in the Ajax request.');
			}
		});
	}

})();
