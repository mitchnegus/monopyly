/*
 * Update an on-screen object and the corresponding database entry.
 *
 * Allow a user to edit a field on-screen (and in the database). When
 * the user clicks a predefined button, the object displaying the value
 * is replaced with an input. The value can be edited in the input, and
 * then this new value is saved after the user takes the focus off of
 * the input or the enter button is pressed.
 */

import { replaceDisplayContentsAjaxRequest } from './update-display-ajax.js';


function updateDBWidget(endpoint, $widget) {

	// Identify the key elements of the widget
	const $button = $widget.find('.widget-edit-button');
	const $display = $widget.find('.widget-display');
	const $input = $widget.find('.widget-input');

	$button.on('click', function() {
		// Hide the edit button while editing
		$button.hide();
		// Set the text of the input to match the displayed value
		$input.val($display.html());
		// Allow the user to enter a new value
		$input.show();
		$input[0].select();
		// Bind the enter key to blur
		$input.on('keydown', function(event) {
			if (event.which == 13) {
					event.preventDefault();
					$input.blur();
			}
		});
	});

	$input.on('blur', function() {
		// Execute an AJAX request to update the database
		const value = $input.val();
		replaceDisplayContentsAjaxRequest(endpoint, value, $display);
		// Show the edit button (on hover) when not editing
		$button.show();
		// Unbind the enter key
		$input.off('keydown');
		// Hide the input box (showing the displayed value)
		$input.delay(50).hide(0);
	});

}


export { updateDBWidget };
