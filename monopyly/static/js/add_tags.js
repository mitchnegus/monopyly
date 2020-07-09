/*
 * Add transaction tags on the 'Transaction Tags' page.
 *
 * Adds a transaction tag under the tag or category corresponding to the
 * plus icon that is clicked. Clicking the plus icon adds a tag shaped
 * input box that accepts a new tag name. Once the input loses focus,
 * an AJAX request is executed and the page is updated. If no tag name
 * was provided, no request occurs.
 */

import { executeAjaxRequest } from './modules/update_display_ajax.js';


(function() {

	const endpoint = NEW_TAG_ENDPOINT;
	// Identify the plus icons
	const $buttons = $('#transaction-tags .new-tag.button'); 

	bindTagCreator($buttons);

	function bindTagCreator($buttons) {
		$buttons.on('click', function() {
			const $container = $(this).closest('.tag-container');
			const $tags = $container.children('ul.tags');
			const $input = $tags.children('input.new-tag');
			// Reveal the input
			$input.slideDown(300, function() {
				$input.addClass('visible');
				$input.focus();
			});
			// Perform actions when focus is lost
			$input.on('blur', function() {
				addNewTag($input, $container, $tags)
			});
		});
	}

	function addNewTag($input, $container, $tags) {
		// Save the input value and prepared to add it to the database as a tag
		const newTagName = $input.val();
		if (newTagName) {
			const parentTag = $container.children('.tag-area').find('.tag').text()
			const rawData = {
				'tag_name': newTagName,
				'parent': parentTag
			};
			// Execute the AJAX request and display update
			function addTag(response) {
				// Add the AJAX request response to the DOM before the input
				$input.before(response);
				// Hide the input again
				$input.hide();
				$input.removeClass('visible');
				// Bind the button for the newly added tag
				const $button = $input.prev().find('.new-tag.button');
				bindTagCreator($button);
			}
			executeAjaxRequest(endpoint, rawData, addTag);
		} else {
			// Hide the input gracefully
			$input.removeClass('visible');
			$input.slideUp(300);
		}
		// Clear the input
		$input.val('');
	}


})();
