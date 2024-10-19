/*
 * Expand a transaction when the plus icon is clicked.
 *
 * Expands a row in the transaction table when the plus icon offering
 * more information is clicked. The expanded row shows transactions in
 * more detail (and a larger font) than the rest of the transaction
 * table. A user can exit the expanded view by clicking the 'x' icon
 * button that is shown in the expanded view. The 'toggleTransactionRow'
 * function takes an optional callback function which is executed after
 * the row is expanded. The callback function receives the selected
 * '.transaction' element as its only argument.
 */

import {
  replaceDisplayContentsAjaxRequest
} from './update-display-ajax.js';


class TransactionToggleManager {
  /**
   * Create the object to toggle transactions.
   *
   * @param {function} callback - A callback function to execute when toggling
   *     a button to get more info.
   */
  constructor(callback = null) {
    // Identify the plus/minus icons
    this.$table = $('.transactions-table');
    this.iconsMoreInfoSelector = '.transaction .more.button';
    this.iconsLessInfoSelector = '.transaction .less.button';
    this.#registerClickExpand(callback);
    this.#registerClickCollapse();
  }

  getButtonTransaction(button) {
    return $(button).closest('.transaction');
  }

  #registerClickExpand(callback) {
    const self = this;
    self.$table.on('click', self.iConsMoreInfoSelector, function(event) {
      const $transaction = self.getButtonTransaction(event.target);
      const toggler = new TransactionToggler($transaction);
      toggler.expand(callback);
      // Do not propagate any additional events up the DOM tree
      // (this avoids recursion in mobile mode when parents are tapped)
      event.stopPropagation();
    });
  }

  #registerClickCollapse() {
    const self = this;
    self.$table.on('click', self.iconsLessInfoSelector, function(event) {
      const $transaction = self.getButtonTransaction(event.target);
      const toggler = new TransactionToggler($transaction);
      toggler.collapse();
      // Do not propagate any additional events up the DOM tree
      // (this avoids recursion in mobile mode when parents are tapped)
      event.stopPropagation();
    });
  }
}


class TransactionToggler {

  /**
   * Create the handler.
   *
   * @param {Object} $transaction - The transaction to be toggled.
   */
  constructor($transaction) {
    // Set timing variables
    this.fadeTime = 200;
    this.slideTime = 250;
    // Identify elements of the row
    this.$transaction = $transaction;
    this.$extendedRow = $transaction.find('.expanded');
    this.$condensedRow = $transaction.find('.condensed');
  }

  /**
   * Expand the transaction
   *
   * @param {function} callback - A callback function to execute when expanding
   *     the transaction information. The callback function takes one argument,
   *     the JQuery object representing the transaction.
   */
  expand(callback = null) {
    // Execute the callback function, if given
    if (callback != null) {
      callback(this.$transaction);
    }
    this.#toggleTransaction(this.$condensedRow, this.$extendedRow);
    this.$transaction.addClass('selected');
  }

  /**
   * Collapse the transaction
   */
  collapse() {
    this.#toggleTransaction(this.$extendedRow, this.$condensedRow);
    this.$transaction.removeClass('selected');
  }

  #toggleTransaction($collapser, $expander) {
    this.#hideSummaryRow($collapser);
    this.#showSummaryRow($expander)
  }

  #hideSummaryRow($row) {
    const self = this;
    $row.fadeTo(self.fadeTime, 0, function() {
      $(this).slideUp(self.slideTime);
    });
  }

  #showSummaryRow($row) {
    const self = this;
    $row.delay(self.fadeTime).slideDown(self.slideTime, function() {
      $(this).fadeTo(self.fadeTime, 1);
    });
  }
}


function displaySubtransactions($transaction) {

    // Execute an AJAX request to get transaction/subtransaction information
    const endpoint = EXPAND_TRANSACTION_ENDPOINT;
    const rawData = $transaction.data("transaction-id");
    const $container = $transaction.find('.subtransaction-container');
    replaceDisplayContentsAjaxRequest(endpoint, rawData, $container);

}


export { TransactionToggleManager, displaySubtransactions };
