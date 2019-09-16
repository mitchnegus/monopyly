/*
 * Provide autocomplete assistance when entering (or update) a transaction.
 *
 * When entering a transaction, provide various autocomplete functionalities
 * for the different types of entries. Autocomplete information is pulled from
 * the database.
 */
var matches;

// Set get possible values for fields with autocomplete
$('div.autocomplete input').on('focus', function() {
	var inputElement = this
	autocompleteAjaxRequest(inputElement);
});

$('div.autocomplete input').on('blur', function() {
	var inputElement = this
	unbindUpdate(inputElement);
	closeAutocomplete(inputElement);
});

function autocompleteAjaxRequest(inputElement) {
	// Return a filtered table for each ID in the set of filterIDs
	$.ajax({
		url: $AUTOCOMPLETE_ENDPOINT,
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
		var userInputMatches = lowerResponseItem.includes(userInput)
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
		var lowerFirstMatch = matches[0].toLowerCase();
		var onlyUserInput = (matchCount == 1 && userInput == lowerFirstMatch);
		if (!onlyUserInput) {
			showAutocomplete(inputElement);
		}
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
	var displayStart = 0;
	var displayCount = 3;
	populateAutocompleteItems(displayStart, displayCount);
	bindNavigation(inputElement, displayStart, displayCount);
}

function clearAutocompleteItems() {
	// Clear all suggestions from the autocomplete list
	$('div.autocomplete-box div.item').remove();
}

function populateAutocompleteItems(displayStart, displayCount) {
	clearAutocompleteItems();
	// Populate the autocomplete list with suggestions
	var autocompleteItem;	
	if (matches.length < displayCount) {
		// Show all suggestions available
		displayStart = 0
		displayCount = matches.length;
	} else if ( matches.length < displayStart + displayCount) {
		// Reset the start so that the "window" doesn't overflow
		displayStart = matches.length - displayCount;
	}
	var displayEnd = displayStart + displayCount;
	for (var i = displayStart; i < displayEnd; i++) {
		autocompleteItem = '<div class="item">' + matches[i] + '</div>';
		$('div.autocomplete-box').append(autocompleteItem);
	}
}

function unbindNavigation (inputElement) {
	$(inputElement).off('keydown');
}

function bindNavigation(inputElement, displayStart, displayCount) {
	// Bind keyboard directions to autocomplete navigation
	var currentFocus = -1;
	$(inputElement).on('keydown', function(event) {
		switch (event.which) {
			case 13:
				event.preventDefault();
				console.log('enter');
				if (currentFocus > -1) {
					// Simulate a click on the active item
					$('div.autocomplete-box div.item.active').click();
				}
				break;
			case 40:
				// Change the current focus 
				if (currentFocus < displayCount) {
					currentFocus++;
				}
				// Keep the display within the limits of the number of matches
				var displayEnd = displayStart + displayCount
				if (currentFocus == displayCount) {
					currentFocus--;
					if (displayEnd < matches.length) {
						displayStart++;
					}
				}
				populateAutocompleteItems(displayStart,	displayCount);
				makeActive(inputElement, currentFocus);
				break;
			case 38:
				// Change the current focus
				if (currentFocus > -1) {
					currentFocus--;
				} 
				// Keep the display within the limits of the number of matches
				if (currentFocus == -1 && displayStart > 0) {
					currentFocus++;
					displayStart--;
				}
				populateAutocompleteItems(displayStart, displayCount);
				makeActive(inputElement, currentFocus);
				break;
		}
	});
}

function makeActive(inputElement, currentFocus) {
	suggestions = $('div.autocomplete-box div.item');
	suggestions.removeClass('active');
	if (currentFocus >= 0) {
		activeSuggestion = suggestions[currentFocus];
		$(activeSuggestion).addClass('active');
		$(activeSuggestion).on('click', function() {
			var text = $(this).text();
			$(inputElement).val(text);
			closeAutocomplete(inputElement);
		});
	}
}
