/*
 * Add and remove overlays to the screen.
 *
 * Opens an interface for adding and removing screen overlays. The
 * interface allows a user to add a simple overlay to the screen, with
 * the ability to exit the overlay dialog either by pressing a button or
 * using the escape key.
 */


/**
 * A class for managing overlays.
 */
class OverlayManager {

  /**
   * Create the manager.
   *
   * @param {JQuery} $container - The container to include the overlay.
   */
  constructor($container) {
    this.$container = $container;
    this.$overlay;
  }

  /**
   * Add the overlay.
   *
   * @param {string} response - The AJAX request response containing the overlay.
   */
  addOverlay(response) {
    this.$container.prepend(response)
    // The overlay container is given the 'overlay' class
    this.$overlay = $('.overlay');
    this.#bindClose();
  }

  /**
   * Bind exit methods to elements in the  overlay.
   */
  #bindClose() {
    this.#bindCloseFromXButtonClick();
    this.#bindCloseFromEscapeKey();
  }

  /**
   * Bind an exit capability to the 'X' button in the overlay.
   */
  #bindCloseFromXButtonClick() {
    const $closeButton = this.$overlay.find('.close.button')
    $closeButton.on('click', this.#closeOverlay.bind(this));
  }

  /**
   * Bind an exit capability to the escape key in the overlay.
   */
  #bindCloseFromEscapeKey() {
    $(window).on('keydown', this.#closeOnEscapePress.bind(this))
  }

  /**
   * Trigger the window to close when the escape key is pressed.
   *
   * @param {Event} event - The event potentially triggering an exit.
   */
  #closeOnEscapePress(event) {
    if (event.which == 27) {
      event.preventDefault();
      this.#closeOverlay();
    }
  }

  /**
   * Close the window.
   */
  #closeOverlay() {
    this.$overlay.remove();
  }

}


export { OverlayManager };
