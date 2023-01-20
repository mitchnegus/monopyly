/*
 * Display an input for a new choice (not in the dropdown).
 *
 * When a user selects the 'New <choice>' option from a dropdown, show
 * an input box for accepting the new choice name. This function takes
 * the field, the select input (dropdown) for the choice, and the text
 * input for the new choice name.
 */


function displayInput($inputChoice, $field) {

  // Set the value for the `New account type` option
  const valueNewChoice = 0;

  $inputChoice.on('change', function() {
    const $choice = $(this).val();
    if ($choice == valueNewChoice) {
      // Show the choice input if the 'New <choice>' option is chosen
      $field.removeClass('hidden');
    } else if ($choice > 0) {
      $field.addClass('hidden');
    }
  });

}


export { displayInput };
