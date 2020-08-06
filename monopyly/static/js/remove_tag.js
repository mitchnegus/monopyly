/*
 * Remove a transaction tag on the 'Transaction Tags' page.
 *
 * Removes the selected transaction tag corresponding to the delete icon
 * that is clicked. After prompting the user to confirm that they do in
 * fact wish to delete the tag, an AJAX request is executed and the tag
 * is removed from the database.
 */

import { executeAjaxRequest } from './modules/update_display_ajax.js';


(function() {
	const endpoint = REMOVE_TAG_ENDPOINT;

	function confirmDelete() {
		return confirm('Are you sure you want to delete this tag?');
	}

	// Identify the delete icons
	const $buttons = $('#transaction-tags .action.button.delete'); 

	$buttons.on('click', function() {
		if (confirmDelete()) {
			const $container = $(this).closest('.tag-container');
			const $tag = $container.find('.tag').first();
			// Remove the tag from the database
			removeTag($tag);
			// Remove the tag from the display
			const $tagContainer = $tag.closest('.tag-area');
			$tagContainer.slideUp(300, function() {
				$(this).remove()
			});
		}
	});

	function removeTag($tag) {
		// Get the name of the tag
		const tagName = $tag.html();
		const rawData = {'tag_name': tagName};
		// Execute the AJAX request 
		executeAjaxRequest(endpoint, rawData);
	}

})();
