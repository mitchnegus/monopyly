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
  // Identify the buttons
  const $createTagButtons = $('#transaction-tags .new-tag.button');
  const $deleteTagButtons = $('#transaction-tags .action.button.delete');
  bindTagButtonBehavior($createTagButtons, $deleteTagButtons);

})();


/**
 * Create the tag manager.
 *
 * @param {JQuery} $createTagButtons - Buttons for adding subtags to one or
 *     more tags.
 * @param {JQuery} $deleteTagButtons - Buttons for removing tags.
 */
function bindTagButtonBehavior($createTagButtons, $deleteTagButtons) {
  console.log('bind create buttons', $createTagButtons);
  console.log('bind delete buttons', $deleteTagButtons);
  $createTagButtons.on('click', function() {
    const $button = $(this);
    const behavior = new TagCreation($button);
    behavior.perform();
  });
  $deleteTagButtons.on('click', function() {
    const $button = $(this);
    const behavior = new TagDeletion($button);
    behavior.perform();
  });
}


/**
 * A class for managing transaction tags and the behavior of their buttons.
 */
class TagButtonBehavior {

  /**
   * Create the tag manager.
   *
   * @param {JQuery} $button - A button belonging to a tag.
   */
  constructor($button) {
    this.$container = $button.closest('.tag-container');
    this.$tag = this.$container.children('.tag-area').find('.tag');
    this.$tags = this.$container.children('ul.tags');
    this.$input = this.$tags.children('input.new-tag');
    // Set animation parameters
    this.slideTime = 300;
  }

}

/**
 * A class for managing transaction tags creation behavior.
 */
class TagCreation extends TagButtonBehavior {

  #endpoint = ADD_TAG_ENDPOINT;

  /**
   * Create the tag creator.
   *
   * @param {JQuery} $button - A button belonging to a tag.
   */
  constructor($button) {
    super($button);
    self = this;
    this.$input.on('blur', function() {
      self.#dropInputFocus();
    });
    this.$input.on('keydown', function() {
      if (event.key == 'Escape') {
        self.#clearInput();
        this.blur();
      } else if (event.key == 'Enter') {
        this.blur();
      }
    });
  }

  /**
   * Perform the behavior.
   */
  perform() {
    this.#showInput();
  }

  /**
   * Show the input box to collect new tag information.
   */
  #showInput() {
    console.log('showing input', this.$input);
    self = this;
    this.$input.slideDown(this.slideTime, function() {
      self.$input.addClass('visible');
      self.$input.focus();
      console.log('focus', self.$input);
    });
  }

  /**
   * Perform a specific action when the input loses focus.
   */
  #dropInputFocus() {
    if (this.$input.val()) {
      this.#createTag();
      this.#hideFilledInput();
    } else {
      this.#hideEmptyInput();
    }
  }

  /**
   * Create the new tag in the database.
   */
  #createTag() {
    const rawData = {
      'tag_name': this.$input.val(),
      'parent': this.$tag.text()
    };
    // Execute the AJAX request and place the new tag
    executeAjaxRequest(this.#endpoint, rawData, this.#placeNewTag.bind(this));
  }

  /**
   * Add the new tag to the DOM before the input.
   */
  #placeNewTag(newTagHTML) {
    const $newTag = $(newTagHTML);
    this.$input.before($newTag);
    // Bind behavior functionality to the newly created/placed tag buttons
    bindTagButtonBehavior(
      $newTag.find('.new-tag.button'), $newTag.find('.action.button.delete')
    );
  }

  /**
   * Hide the input immediately.
   */
  #hideFilledInput() {
    this.$input.hide();
    this.$input.removeClass('visible');
    this.#clearInput();
  }

  /**
   * Hide the (empty) input gracefully.
   */
  #hideEmptyInput() {
    this.$input.removeClass('visible');
    this.$input.slideUp(this.slideTime);
    console.log('hiding empty input', this.$input);
  }

  /**
   * Clear the input.
   */
  #clearInput() {
    this.$input.val('');
  }

}


/**
 * A class for managing transaction tags deletion behavior.
 */
class TagDeletion extends TagButtonBehavior {

  #endpoint = REMOVE_TAG_ENDPOINT;

  /**
   * Perform the behavior.
   */
  perform() {
    if (this.#confirmDelete()) {
      this.#removeTag();
    }
  }

  /**
   * Remove the tag from the database.
   */
  #removeTag() {
    const rawData = {'tag_name': this.$tag.html()};
    // Execute the AJAX request to delete the tag
    executeAjaxRequest(this.#endpoint, rawData);
    // Remove the tag from the display
    this.$container.slideUp(this.slideTime, function() {this.remove()});
  }

  #confirmDelete() {
    return confirm('Are you sure you want to delete this tag?');
  }

}
