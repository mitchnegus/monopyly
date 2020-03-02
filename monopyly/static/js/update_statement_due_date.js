/*
 * Update a credit card statement's due date.
 *
 * When a user clicks the `edit-due-date` icon on the statemeent details
 * page, this script changes the displayed due date into a text box
 * where a user can edit the date. The text box completes an AJAX
 * request when it loses focus, and if the input is given in an
 * acceptable format, the new date is saved and the displayed due date
 * is updated. If not, the existing statement due date in the database
 * is preserved and displayed.
 */

// Identify the key elements
let $buttonEdit = $('#edit-due-date-icon');
let $displayDueDate = $('#statement-info #payment #due #due-date');
let $inputDueDate = $('#statement-info #payment #due #edit-due-date');

$buttonEdit.on('click', function() {
	// Hide the edit button while editing
	$buttonEdit.hide();
	// Allow the user to enter a due date
	$displayDueDate.hide();
	$inputDueDate.show();
	$inputDueDate[0].select();
	// Set the text of the input to match the set due date
	$inputDueDate.val($displayDueDate.html());
	// Bind the enter key to blur
	$inputDueDate.on('keydown', function(event) {
		if (event.which == 13) {
				event.preventDefault();
				$inputDueDate.blur();
		}
	});
});

$inputDueDate.on('blur', function() {
	// Show the edit button (on hover) when not editing
	$buttonEdit.show();
	// Hide the input box and show the database due date
	$inputDueDate.hide();
	$displayDueDate.show();
	// Execute an AJAX request to update the database
	updateStatementDueDateAjaxRequest();
	// Unbind the enter key
	$inputDueDate.off('keydown');
});

function updateStatementDueDateAjaxRequest() {
	// Return the newly updated statement date
	$.ajax({
		url: UPDATE_STATEMENT_DUE_DATE_ENDPOINT,
		type: 'POST',
		data: JSON.stringify($inputDueDate.val()),
		contentType: 'application/json; charset=UTF-8',
		success: function(response) {
			$displayDueDate.html(response)
		},
		error: function(xhr) {
			console.log('There was an error in the Ajax request.');
		}
	});
}
