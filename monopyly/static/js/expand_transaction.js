/*
 * Expand a transaction when the plus icon is clicked.
 *
 * Expands a row in the transaction table when the plus icon offering
 * more information is clicked. The expanded row shows transactions in
 * more detail (and a larger font) than the rest of the transaction
 * table. A user can exit the expanded view by clicking the minus icon
 * button that is shown in the expanded view.
 */

(function() {

	const durationFadeCompact = 100
	const durationSlideCompact = 200
	const durationSlideExpanded = durationFadeCompact + durationSlideCompact
	const durationFadeExpanded = 200
	// Identify the plus/minus icons
	const $iconsMoreInfo = $('tr.compact .more');
	const $iconsLessInfo = $('tr.expanded .less');
	// Initially hide all extra details
	$('tr.expanded .details').hide();

	$iconsMoreInfo.on('click', function() {
		const $compactRow = $(this).closest('tr');
		const $expandedRow = $compactRow.next('tr');
		showDetails($compactRow, $expandedRow);
	});

	$iconsLessInfo.on('click', function() {
		const $expandedRow = $(this).closest('tr');
		const $compactRow = $expandedRow.prev('tr');
		hideDetails($compactRow, $expandedRow);
	});

	function showDetails($compactRow, $expandedRow) {
		const delay = 10
		// Hide the compact transaction row
		const $compactDetails = $compactRow.find('.detail');
		$compactDetails.fadeTo(durationFadeCompact, 0, function() {
			$(this).slideToggle(durationSlideCompact);
		});
		// Show the expanded transaction row
		const $expandedDetails = $expandedRow.find('.details');
		$expandedDetails.slideToggle(durationSlideExpanded, function() {
			$(this).delay(delay).fadeTo(durationFadeExpanded, 1);
		});
	}

	function hideDetails($compactRow, $expandedRow) {
		const delay = durationFadeExpanded + 10
		// Hide the expanded transaction row
		const $expandedDetails = $expandedRow.find('.details');
		$expandedDetails.fadeTo(durationFadeExpanded, 0, function() {
			$(this).delay(delay).slideToggle(durationSlideExpanded);
		});
		// Show the compact transaction row
		const $compactDetails = $compactRow.find('.detail');
		$compactDetails.delay(delay).slideToggle(durationSlideCompact, function() {
			$(this).fadeTo(durationFadeCompact, 1);
		});
	}

})();
