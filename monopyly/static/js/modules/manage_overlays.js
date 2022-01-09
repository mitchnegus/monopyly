/*
 * Add and remove overlays to the screen.
 *
 * Opens an interface for adding and removing screen overlays. The
 * interface allows a user to add a simple overlay to the screen, with
 * the ability to exit the overlay dialog either by pressing a button or
 * using the escape key.
 */


class OverlayManager {
  // A class for handling overlays
  constructor($container) {
    this.$container = $container;
    this.$overlay;
  }

  addOverlay(response) {
    // Add an overlay, described by the AJAX request response
    this.$container.prepend(response)
    // The overlay container is given the 'overlay' class
    this.$overlay = $('.overlay');
    this.#bindClose();
  }

  #bindClose() {
    this.#bindCloseFromXButtonClick();
    this.#bindCloseFromEscapeKey();
  }

  #bindCloseFromXButtonClick() {
    // Close the overlay when the 'X' button is clicked
    const $closeButton = this.$overlay.find('.close.button')
    $closeButton.on('click', this.#closeOverlay.bind(this));
  }

  #bindCloseFromEscapeKey() {
    // Close the overlay when the escape key is pressed
    const manager = this;
    $(window).on('keydown', this.#closeOnEscapePress.bind(this))
  }

  #closeOnEscapePress(event) {
    if (event.which == 27) {
      event.preventDefault();
      this.#closeOverlay();
    }
  }

  #closeOverlay() {
    this.$overlay.remove();
  }

}


export { OverlayManager };

