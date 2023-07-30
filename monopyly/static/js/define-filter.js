/*
 * Define behavior for the card filter.
 *
 * Specify the behavior for the credit card fitler. These behaviors
 * include providing information to the user about card status
 * (active/inactive) when the filter is hovered over and dimming filters
 * that are unselected.
 */

(function() {

	// Identify the card filters
	const $filterContainer = $('#card-filter');

	// Label inactive cards when they are hovered over
	const inactiveCardFilters = $filterContainer.find('.inactive.card');
	let defaultText;
	inactiveCardFilters.hover(
		// Change text when hovering over the filter
		function() {
			const $this = $(this);
			const defaultWidth = $this.width();
			defaultText = $this.text();
			// Change the text, maintain the width
			$this.text('Inactive Card');
			$this.width(defaultWidth);
		},
		function() {
			// Replace the changed text
			const $this = $(this);
			$this.text(defaultText);
		}
	);

	// Change the filter status on click
	const $filters = $filterContainer.find('.card');
	$filters.on('click', function() {
		// Add or remove the selected tag when clicked
		$(this).toggleClass('selected');
	});

})();
