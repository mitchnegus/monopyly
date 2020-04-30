/*
 * Expand a transaction when the plus icon is clicked.
 *
 * Expands a row in the transaction table when the plus icon offering
 * more information is clicked. The expanded row shows transactions in
 * more detail (and a larger font) than the rest of the transaction
 * table. A user can exit the expanded view by clicking the 'x' icon
 * button that is shown in the expanded view.
 */

(function() {

	// Identify the plus/minus icons
	const $iconsMoreInfo = $('.transaction .more.button');
	const $iconsLessInfo = $('.transaction .less.button');

	$iconsMoreInfo.on('click', function() {
		const $transaction = $(this).closest('.transaction');
		$transaction.addClass('expanded');
	});

	$iconsLessInfo.on('click', function() {
		const $transaction = $(this).closest('.transaction');
		$transaction.removeClass('expanded');
	});

})();
