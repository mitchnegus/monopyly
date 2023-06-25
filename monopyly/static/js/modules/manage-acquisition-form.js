/**
 * Display an input for a new choice (not in the dropdown).
 *
 * When a user selects the 'New <choice>' option from a dropdown, show
 * an input box for accepting the new choice name. This function takes
 * the field, the select input (dropdown) for the choice, and the text
 * input for the new choice name.
 */


/**
 * A class for displaying/hiding elements of 'Acquisition Forms'.
 */
class AcquisitionFormManager {

  #newChoiceSelectValue = 0;
  #unsetChoiceSelectValue = -1;
  #unsetInputValue = "";
  /**
   * Create the manager.
   *
   * @param {JQuery} $choiceSelect - The select field being used to make a
   *     selection.
   * @param {JQuery} $affectField - The field to show when a 'New <choice>`.
   *     option is chosen
   */
  constructor($choiceSelect, $affectField) {
    this.$choiceSelect = $choiceSelect;
    this.$affectField = $affectField;
    this.$affectInputs = $affectField.find("input");
    this.$affectSelects = $affectField.find("select");
    // Register the event listener
    $choiceSelect.on("change", this.#changeForm.bind(this));
  }

  /**
   * Change the form structure depending on the choice input value.
   */
  #changeForm() {
    const newChoice = this.$choiceSelect.val();
    if (newChoice == this.#newChoiceSelectValue) {
      this.#showField();
    } else if (newChoice > this.#newChoiceSelectValue) {
      this.#hideField();
    }
  }

  /**
   * Show the field to accept new inputs (and enable it).
   */
  #showField() {
    this.$affectField.removeClass("hidden");
    // Enable inputs belonging to this field
    this.$affectInputs.prop("disabled", false);
  }

  /**
   * Hide the field to accept new inputs (and disable it).
   */
  #hideField() {
    this.$affectField.addClass("hidden");
    // Disable inputs belonging to this field, and reset their values
    this.$affectInputs.prop("disabled", true);
    // Also reset the input values to their initial values
    this.$affectInputs.val(this.#unsetInputValue);
    this.$affectSelects.val(this.#unsetChoiceSelectValue);
  }

}


export { AcquisitionFormManager };
