/*
 * Add transaction tags on the 'Transaction Tags' page.
 *
 * Adds a transaction tag under the tag or category corresponding to the
 * plus icon that is clicked. Clicking the plus icon adds a tag shaped
 * input box that accepts a new tag name. Once the input loses focus,
 * an AJAX request is executed and the page is updated. If no tag name
 * was provided, no request occurs.
 */

import { updateDisplayAjaxRequest } from './modules/update_display_ajax.js';


(function() {

	const endpoint = NEW_TAG_ENDPOINT;
	// Identify the plus icons
	const $iconsNewTag = $('#transaction-tags .new-tag.button'); 
	const $inputs = $('input.new-tag');

	$iconsNewTag.on('click', function() {
		const $container = $(this).closest('.tag-container');
		const $tags = $container.children('ul.tags');
		const $input = $tags.children('input.new-tag');
		// Reveal the input
		$input.slideDown(300, function() {
			$(this).addClass('visible');
			$(this).focus();
		});
	});

	$inputs.on('blur', function() {
		const $input = $(this);
		const $container = $input.closest('.tag-container');
		// Hide the input
		$input.removeClass('visible')
		$input.slideUp(300);
		// Save the input value and add it to the database as a tag
		const newTagName = $input.val();
		if (newTagName) {
			const rawData = {'tag_name': newTagName};
			if ($input.attr('name') == 'category') {
				// Category input (find the parent)
				const $parentCategoryObject = $container.children('.category');
				const parentCategory = $parentCategoryObject.find('.tag').text();
				if (parentCategory) {
					rawData['parent'] = parentCategory;
				} else {
					rawData['parent'] = 'root';
				}
				// Update the categories
				const $display = $('#categories-container');
				updateDisplayAjaxRequest(endpoint, rawData, $display);
			} else {
				// Tag input; update the tags
				const $display = $('#tags-container');
				updateDisplayAjaxRequest(endpoint, rawData, $display);
			}
		}
	});

})();
