/*
 * Expand a transaction when the plus icon is clicked.
 *
 * Expands a row in the transaction table when the plus icon offering
 * more information is clicked. The expanded row shows transactions in
 * more detail (and a larger font) than the rest of the transaction
 * table. A user can exit the expanded view by clicking the 'x' icon
 * button that is shown in the expanded view.
 */
import {
	replaceDisplayContentsAjaxRequest
} from './modules/update_display_ajax.js';


(function() {

	// Identify the plus/minus icons
	const $iconsMoreInfo = $('.transaction .more.button');
	const $iconsLessInfo = $('.transaction .less.button');
	// Set timing variables
	const fadeTime = 200;
	const slideTime = 250;

	$iconsMoreInfo.on('click', function() {
		// Get the transaction object
		const $transaction = $(this).closest('.transaction');
		// Hide the condensed transaction summary
		const $condensedRow = $transaction.find('.condensed');
		$condensedRow.fadeTo(fadeTime, 0, function() {
			$(this).slideUp(slideTime);
		});
		// Execute the AJAX request to get transaction/subtransaction information
		const endpoint = EXPAND_TRANSACTION_ENDPOINT;
		const rawData = $transaction[0].id;
		const $container = $transaction.find('.subtransaction-container');
		replaceDisplayContentsAjaxRequest(endpoint, rawData, $container);
		$transaction.addClass('selected');
		// Show the expanded transaction summary
		const $expandedRow = $transaction.find('.expanded');
		$expandedRow.delay(fadeTime).slideDown(slideTime, function() {
			$(this).fadeTo(fadeTime, 1);
		});
	});

	$iconsLessInfo.on('click', function() {
		// Get the transaction object
		const $transaction = $(this).closest('.transaction');
		$transaction.removeClass('selected');
		// Hide the expanded transaction summary
		const $expandedRow = $transaction.find('.expanded');
		$expandedRow.fadeTo(fadeTime, 0, function() {
			$(this).slideUp(slideTime);
		})
		// Show the condensed transaction summary
		const $condensedRow = $transaction.find('.condensed');
		$condensedRow.slideDown(slideTime, function() {
			$(this).fadeTo(fadeTime, 1);
		});
	});

})();
