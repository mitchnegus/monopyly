/*
 * Add a transaction tag on the 'Transaction Tags' page.
 *
 * Adds a transaction tag under the tag or category corresponding to the
 * plus icon that is clicked. Clicking the plus icon adds a tag shaped
 * input box that accepts a new tag name. Once the input loses focus,
 * an AJAX request is executed, the database is updated and the tree of
 * transactions is partially refreshed to allow further additions. If no
 * tag name was provided, no request occurs.
 */

import { executeAjaxRequest } from './modules/ajax.js';


(function() {

  const endpointAddTag = ADD_TAG_ENDPOINT;
  const endpointRemoveTag = REMOVE_TAG_ENDPOINT;
  // Set animation parameters
  const slideTime = 300;
  // Identify the buttons
  const $buttonsAddTag = $('#transaction-tags .new-tag.button');
  const $buttonsDelete = $('#transaction-tags .action.button.delete');

  bindTagCreator($buttonsAddTag, $buttonsDelete);

  function bindTagCreator($buttonsAddTag, $buttonsDelete) {
    // Bind add tag buttons
    $buttonsAddTag.on('click', function() {
      const $container = $(this).closest('.tag-container');
      const $tags = $container.children('ul.tags');
      const $input = $tags.children('input.new-tag');
      // Reveal the input
      showInput($input);
      // Perform actions when focus is lost
      $input.on('blur', function() {
        if ($input.val()) {
          addNewTag($input, $container);
        } else {
          hideEmptyInput($input);
        }
        clearInput($input);
      });
      $input.on('keydown', function() {
        if (event.which == 27) {
          clearInput($input);
          hideEmptyInput($input);
        }
      });
    });
    // Bind remove tag buttons
    $buttonsDelete.on('click', function() {
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
  }

  function addNewTag($input, $container) {
    // Add the input value to the database as a tag
    const parentTag = $container.children('.tag-area').find('.tag').text()
    const rawData = {
      'tag_name': $input.val(),
      'parent': parentTag
    };
    // Execute the AJAX request and display update
    function addTag(response) {
      // Add the AJAX request response to the DOM before the input
      $input.before(response);
      hideFilledInput($input);
      // Bind the buttons for the newly added tag
      const $buttonAddTag = $input.prev().find('.new-tag.button');
      const $buttonRemoveTag = $input.prev().find('.action.button.delete');
      bindTagCreator($buttonAddTag, $buttonRemoveTag);
    }
    executeAjaxRequest(endpointAddTag, rawData, addTag);
  }

  function showInput($input) {
    $input.slideDown(slideTime, function() {
      $input.addClass('visible');
      $input.focus();
    });
  }

  function hideFilledInput($input) {
    // Hide the input immediately
    $input.hide();
    $input.removeClass('visible');
  }

  function hideEmptyInput($input) {
    // Hide the input gracefully
    $input.removeClass('visible');
    $input.slideUp(slideTime);
  }

  function clearInput($input) {
    // Clear the input
    $input.val('');
  }

  function confirmDelete() {
    return confirm('Are you sure you want to delete this tag?');
  }

  function removeTag($tag) {
    // Get the name of the tag
    const tagName = $tag.html();
    const rawData = {'tag_name': tagName};
    // Execute the AJAX request
    executeAjaxRequest(endpointRemoveTag, rawData);
  }

})();
