/*
 * Define behavior for the card filter.
 *
 * Specify the behavior for the credit card fitler. These behaviors
 * include providing information to the user about card status
 * (active/inactive) when the filter is hovered over and dimming filters
 * that are unselected.
 */

// Identify the card filters
var filterContainer = $('#card-filter');

// Label inactive cards when they are hovered over
var inactiveCardFilters = filterContainer.find('.inactive.card');
var defaultText, defaultWidth;
inactiveCardFilters.hover(
	function () {
		var $this = $(this);
		defaultText = $this.text();
		defaultWidth = $this.width();
		// Change the text, maintain the width
		$this.text('Inactive Card');
		$this.width(defaultWidth);
	},
	function() {
		var $this = $(this);
		$this.text(defaultText);
	}
);

// Change the filter status on click
var filters = filterContainer.find('.card');
filters.on('click', function() {
	// Add or remove the selected tag when clicked
	$(this).toggleClass('selected');
});

