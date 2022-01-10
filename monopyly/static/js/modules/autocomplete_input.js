/*
 * Execute the autocomplete interface when using an input element.
 *
 * Opens an interface for suggesting input values when a user interacts
 * with a form input. The interface can be navigated using the tab and
 * enter keys, and attempts to be as intuitive as possible.
 */

import { executeAjaxRequest } from './ajax.js';


function anchoredMatch(string1, string2) {
  if (string2.startsWith(string1)) {
    return true;
  } else {
    return false;
  }
}


function containedMatch(string1, string2) {
  if (string2.includes(string1)) {
    return true;
  } else {
    return false;
  }
}


class AutocompleteBox {
  // A box for displaying autocomplete suggestions
  defaultBoxSize = 10;
  defaultBoxStartIndex = 0;
  $inputElements = $('form input');
  boxTags = '<div class="autocomplete-box"></div>';
  matches;
  response;
  currentFocus;

  constructor(inputElement) {
    this.inputElement = inputElement;
    this.boxSize = this.defaultBoxSize;
    this.boxStartIndex = this.defaultBoxStartIndex;
    this.$boxElement;
    this.$boxSuggestions;
    // Bind the update method to any input action
    $(this.inputElement).off('input'); // prevent duplicate element focusing
    $(this.inputElement).on('input', this.update.bind(this));
  }

  release() {
    this.close();
    $(this.inputElement).off('input');
  }

  get boxEndIndex() {
    return this.boxStartIndex + this.boxSize;
  }

  load_response(response) {
    this.response = response;
  }

  ajaxRequest(endpoint, rawData) {
    // Execute an AJAX request to find matches
    executeAjaxRequest(endpoint, rawData, this.load_response.bind(this));
  }

  update() {
    // Update the box (opening or closing it if necessary)
    const userInput = this.inputElement.value;
    if (this.#needsRefresh(userInput)) {
      if (!this.$boxElement) {
        this.open();
      }
      this.refresh();
    } else {
      this.close();
    }
  }

  open() {
    // Open the autocomplete box
    $(this.inputElement).parent().append(this.boxTags);
    this.$boxElement = $('div.autocomplete-box');
    this.#bindKeyboardAction();
  }

  close() {
    // Close the autocomplete box
    this.clear();
    if (this.$boxElement) {
      this.$boxElement.remove();
    }
    this.$boxElement = null;
    this.#unbindKeyboardAction();
  }

  refresh() {
    // Refresh the box by clearing old suggestions and populating with new ones
    this.clear();
    this.populate();
  }

  clear() {
    // Clear the suggestions in the autocomplete box
    if (this.$boxSuggestions) {
      this.$boxSuggestions.remove();
    }
  }

  populate() {
    // Populate the autocomplete box with suggestions
    this.#setBoxRange();
    for (let i = this.boxStartIndex; i < this.boxEndIndex; i++) {
      const suggestion = '<div class="item">' + this.matches[i] + '</div>';
      this.$boxElement.append(suggestion);
    }
    this.$boxSuggestions = $('div.autocomplete-box div.item');
    this.#bindMouseAction();
  }

  select(suggestion) {
    // Select a suggestion from the list
    if (suggestion !== null) {
      this.fill(suggestion);
    }
    this.close();
    this.advanceFocus();
  }

  fill(suggestion) {
    // Populate the input element text using the chosen suggestion
    this.inputElement.value = suggestion.textContent;
  }

  advanceFocus(inputElement) {
    // Shift the focus to the next input element
    const nextInputIndex = this.$inputElements.index(this.inputElement)+1;
    this.$inputElements.eq(nextInputIndex).focus();
  }

  #needsRefresh(userInput) {
    // Check if the list of matches needs to be refreshed
    this.#refreshMatches(userInput);
    const matchCount = this.matches.length;
    const matchIsUserInput = (matchCount == 1 && userInput == this.matches[0]);
    if (matchCount < 1 || matchIsUserInput || !userInput) {
      return false;
    } else {
      return true;
    }
  }

  #refreshMatches(userInput) {
    // Refresh autocomplete suggestions using the AJAX response
    this.matches = [];
    this.#testMatches(userInput, anchoredMatch);
    this.#testMatches(userInput, containedMatch);
  }

  #testMatches(userInput, testFunction) {
    // Add responses matching the user input to the set of matching suggestions
    for (let i = 0; i < this.response.length; i++) {
      const responseSuggestion = this.response[i];
      // Test (lowercase) match status and if already recorded
      const lowercaseSuggestion = responseSuggestion.toLowerCase();
      const lowercaseInput = userInput.toLowerCase();
      const isMatch = testFunction(lowercaseInput, lowercaseSuggestion);
      const isNotYetIncluded = !this.matches.includes(responseSuggestion);
      if (isMatch && isNotYetIncluded) {
        // Add new matches to the list of suggestions
        this.matches.push(responseSuggestion);
      }
    }
  }

  #setBoxRange() {
    // Set the range of the autocomplete box
    this.boxSize = Math.min(this.matches.length, this.defaultBoxSize);
    if (this.boxEndIndex > this.matches.length) {
      // Box overextends available matches; reset the starting point
      this.boxStartIndex = this.matches.length - this.boxSize;
    }
  }

  #bindMouseAction() {
    // Bind mouse action functionality to each suggestion
    this.$boxSuggestions.on('mousedown', function(e) {
      // Prevent "premature" blurring
      e.preventDefault();
    });
    let box = this;
    this.$boxSuggestions.on('click', function() {
      box.select(this);
    });
  }

  #bindKeyboardAction() {
    // Bind functionality to keyboard actions for each suggestion
    let box = this;
    box.currentFocus = -1;
    $(this.inputElement).on('keydown', function(event) {
      switch (event.which) {
        case 13:    // ENTER
          event.preventDefault();
          box.#selectActiveSuggestion();
          break;
        case 9:     // TAB
          event.preventDefault();
          if (event.shiftKey) {
            box.#moveCursorUp();
          } else {
            box.#moveCursorDown();
          }
          break;
        case 38:    // UP
          event.preventDefault();
          box.#moveCursorUp();
          break;
        case 40:    // DOWN
          event.preventDefault();
          box.#moveCursorDown();
          break;
      }
    });
  }

  #selectActiveSuggestion() {
    // Select the highlighted 'active' suggestion
    const notOnText = (this.currentFocus != -1);
    let suggestion;
    if (notOnText) {
      suggestion = $('div.autocomplete-box div.item.active')[0];
    } else {
      suggestion = null;
    }
    this.select(suggestion);
  }

  #moveCursorUp() {
    // Move the cursor up (depending on the box window)
    const notOnText = (this.currentFocus > -1);
    const atTop = (this.currentFocus == 0);
    const matchesRemainAbove = (this.boxStartIndex > 0);
    if (notOnText) {
      if (atTop && matchesRemainAbove) {
        this.boxStartIndex--;
      } else {
        this.currentFocus--;
      }
    }
    this.refresh()
    this.#highlight();
  }

  #moveCursorDown() {
    // Move the cursor down (depending on the box window)
    const notAtBottom = (this.currentFocus < this.boxSize - 1);
    const atBottom = (this.currentFocus == this.boxSize - 1);
    const matchesRemainBelow = (this.boxEndIndex < this.matches.length);
    if (notAtBottom) {
      this.currentFocus++;
    } else if (atBottom && matchesRemainBelow) {
      this.boxStartIndex++;
    }
    this.refresh();
    this.#highlight();
  }

  #highlight() {
    // Highlight the suggestion as the 'active' suggestion
    this.$boxSuggestions.removeClass('active');
    if (this.currentFocus >= 0) {
      const activeSuggestion = this.$boxSuggestions[this.currentFocus];
      activeSuggestion.classList.add('active');
    }
  }

  #unbindKeyboardAction() {
    // Unbind keyboard action functionality from all suggestions
    $(this.inputElement).off('keydown');
  }

}


export { AutocompleteBox };

