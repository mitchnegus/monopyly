/*
 * Provide autocomplete suggestions when filling out a transaction form.
 *
 * When entering a transaction, provide autocomplete suggestions to the
 * user. The suggestions are pulled from the database for the field
 * being input using an AJAX request. They are ordered (on the server
 * side) by their occurrence frequecy and then filtered here by the
 * current input text after the input field is changed.
 */

// Identify all input elements in the form
var $inputElements = $('form input');
// Set global variables for selection movement
var matches;
var displayStart, displayCount;
var currentFocus;

// Get possible values for fields with autocomplete
$('div.autocomplete input').on('focus', function() {
	var inputElement = this;
	autocompleteAjaxRequest(inputElement);
});

$('div.autocomplete input').on('blur', function() {
	var inputElement = this
	unbindUpdate(inputElement);
	closeAutocomplete(inputElement);
});

function autocompleteAjaxRequest(inputElement) {
	// Return a set of autocomplete suggestions from the database
	$.ajax({
		url: AUTOCOMPLETE_ENDPOINT,
		type: 'POST',
		data: JSON.stringify(inputElement.id),
		contentType: 'application/json; charset=UTF-8',
		success: function(response) {
			// Define variables for the user input and its database matches
			var existingUserInput = $(inputElement).val().toLowerCase();
			// Refresh the set of matches and update the menu
			refreshMatches(existingUserInput, response);
			updateAutocomplete(inputElement, existingUserInput);
			// Bind keyup to also perform update, arrow keys to navigate
			bindUpdate(inputElement, response);
		},
		error: function(xhr) {
			console.log('There was an error in the Ajax request.');
		}
	});
}

function unbindUpdate(inputElement) {
	// Unbind the keyup behavior
	$(inputElement).off('input');
}

function bindUpdate(inputElement, response) {
	// Bind any input action to refresh/update autocomplete
	$(inputElement).on('input', function() {
		var userInput = $(this).val().toLowerCase();
		// Check the user input against the Ajax response
		refreshMatches(userInput, response);
		// Update the autocomplete menu (including showing/hiding the menu)
		updateAutocomplete(inputElement, userInput);
	});
}

function refreshMatches(userInput, response) {
	// Refresh autocomplete matches against Ajax response
	matches = [];
	var responseItem, lowerResponseItem;
	// First check if the response starts with the user input substring
	for (var i = 0; i < response.length; i++) {
		responseItem = response[i];
		lowerResponseItem = responseItem.toLowerCase();
		if (lowerResponseItem.startsWith(userInput)) {
			matches.push(responseItem);
		}
	}
	// Second, check if the reponse contains the user input substring anywhere
	for (var i = 0; i < response.length; i++) {
		responseItem = response[i] 
		var lowerResponseItem = responseItem.toLowerCase();
		var userInputMatches = lowerResponseItem.includes(userInput);
		var responseItemIncluded = matches.includes(responseItem);
		if (userInputMatches && !responseItemIncluded) {
			matches.push(responseItem);
		}
	}
}

function updateAutocomplete(inputElement, userInput) {
	// Define conditions for showing/closing the autocomplete box
	var matchCount = matches.length;
	if (userInput && matchCount) {
		// There is user input and some matches, so show the autocomplete box
		var lowerFirstMatch = matches[0].toLowerCase();
		var onlyUserInput = (matchCount == 1 && userInput == lowerFirstMatch);
		if (!onlyUserInput) {
			// Don't show a suggestion if the given input matches the only suggestion
			showAutocomplete(inputElement);
		}
	} else {
		// There is either no input or no matches, so close the autocomplete box
		closeAutocomplete(inputElement);
	}
}

function closeAutocomplete(inputElement) {
	$('div.autocomplete-box').remove();
	unbindNavigation(inputElement);
}

function showAutocomplete(inputElement) {
	closeAutocomplete(inputElement);
	// Define the outer autocomplete box
	var autocompleteBox = '<div class="autocomplete-box"></div>';
	$(inputElement).parent().append(autocompleteBox);
	// Define each item within the autocomplete box
	var displayStartDefault = 0;
	var displayCountDefault = 10;
	displayStart = displayStartDefault;
	displayCount = displayCountDefault;
	populateAutocompleteItems(inputElement);
	bindNavigation(inputElement);
}

function clearAutocompleteItems() {
	// Clear all suggestions from the autocomplete list
	$('div.autocomplete-box div.item').remove();
}

function populateAutocompleteItems(inputElement) {
	clearAutocompleteItems();
	// Populate the autocomplete list with suggestions
	var autocompleteItem;	
	var $suggestions;
	if (matches.length < displayCount) {
		// Show all suggestions available
		displayCount = matches.length;
	} else if (matches.length < displayStart + displayCount) {
		// Reset the starting point to the fixed number of suggestions above bottom
		displayStart = matches.length - displayCount;
	}
	var displayEnd = displayStart + displayCount;
	for (var i = displayStart; i < displayEnd; i++) {
		autocompleteItem = '<div class="item">' + matches[i] + '</div>';
		$('div.autocomplete-box').append(autocompleteItem);
	}
	$suggestions = $('div.autocomplete-box div.item');
	$suggestions.on('mousedown', function(e) {
		// Prevent "premature" blurring
		e.preventDefault();
	});
	$suggestions.on('click', function() {
		$suggestion = $(this);
		autofillReplacement($suggestion, inputElement);
		var nextInputIndex = $inputElements.index(inputElement)+1;
		$inputElements.eq(nextInputIndex).focus();
	});
}

function unbindNavigation (inputElement) {
	$(inputElement).off('keydown');
}

function bindNavigation(inputElement) {
	// Bind keyboard directions to autocomplete navigation
	currentFocus = -1;
	$(inputElement).on('keydown', function(event) {
		switch (event.which) {
			case 13: 		// ENTER
				event.preventDefault();
				selectItem(inputElement);
				break;
			case 9: 		// TAB
				event.preventDefault();
				if (event.shiftKey) {
					moveUp(inputElement);
				} else {
					moveDown(inputElement);
				}
				break;
			case 40: 		// DOWN
				event.preventDefault();
				moveDown(inputElement);
				break;
			case 38: 		// UP
				event.preventDefault();
				moveUp(inputElement);
				break;
		}
	});
}

function selectItem(inputElement) {
	if (currentFocus > -1) {
		// Simulate a click on the active item
		$suggestion = $('div.autocomplete-box div.item.active');
		autofillReplacement($suggestion, inputElement);
	}
	closeAutocomplete(inputElement);
	var nextInputIndex = $inputElements.index(inputElement)+1;
	$inputElements.eq(nextInputIndex).focus();
}

function moveDown(inputElement) {
	// Change the current focus 
	if (currentFocus < displayCount - 1) {
		currentFocus++;
	}
	// Keep the display within the limits of the number of matches
	if (currentFocus == displayCount - 1) {
		var displayEnd = displayStart + displayCount;
		if (displayEnd < matches.length) {
			displayStart++;
		}
	}
	populateAutocompleteItems(inputElement);
	makeActive(currentFocus);
}

function moveUp(inputElement) {
	// Change the current focus
	if (currentFocus > -1) {
		// Keep the display within the limits of the number of matches
		if (currentFocus == 0 && displayStart > 0) {
			displayStart--;
		} else {
			currentFocus--;
		}
	} else if (currentFocus == -1) {

	} 
	populateAutocompleteItems(inputElement);
	makeActive(currentFocus);
}

function makeActive(currentFocus) {
	var $suggestions, activeSuggestion
	$suggestions = $('div.autocomplete-box div.item');
	$suggestions.removeClass('active');
	if (currentFocus >= 0) {
		activeSuggestion = $suggestions[currentFocus];
		$(activeSuggestion).addClass('active');
	}
}

function autofillReplacement($suggestion, inputElement) {
	var text = $suggestion.text();
	$(inputElement).val(text);
	closeAutocomplete(inputElement);
}
