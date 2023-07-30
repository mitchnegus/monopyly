/*
 * Highlight transactions with discrepancies on the reconcilation page.
 */


/**
 * A class for highlighting transaction/activity discrepancies.
 */
class DiscrepancyHighlighter {

  /**
   * Create the highlighter.
   */
  constructor() {
    const highlighter = this;
    this.$transactionContainer = $("#statement-transactions-container");
    const $transactions = this.$transactionContainer.find(".transaction");
    this.$transactionRows = $transactions.find(".condensed .row-content");
    this.$discrepantActivities = $(".discrepant-activity");
    // Toggle highlighting based on clicking
    this.clickedTransactionID = null;
    this.$discrepantActivities.on("click", function() {
      highlighter.toggleClickTransactionHighlight(this);
    });
    // Toggle highlighting based on hovering
    this.$discrepantActivities.hover(
      function() {highlighter.addHoverTransactionHighlight(this)},
      function() {highlighter.removeHoverTransactionHighlight(this)},
    )
    // Remove highlighting if anywhere else on the page is clicked
    $(document).on("click", function(event) {
      const $target = $(event.target);
      if (highlighter.#isExtraneousClick($target)) {
        highlighter.removeHighlight(
          highlighter.$discrepantActivities, highlighter.$transactionRows
        );
      }
    });
  }

  #isExtraneousClick($target) {
    const isNotDiscrepantActivity = (
      $target.closest(this.$discrepantActivities).length == 0
    );
    const isNotTransactionContainer = (
      $target.closest(this.$transactionContainer).length == 0
    );
    return isNotDiscrepantActivity && isNotTransactionContainer;
  }

  /**
   * Get the transaction (row) from the container with matching transaction ID.
   *
   * @param {object} activity - The activity object to match.
   */
  getMatchingTransactionRow(activity) {
    const transactionID = activity.dataset.transactionId;
    const selector = `.transaction[data-transaction-id='${transactionID}']`;
    return this.$transactionContainer.find(selector).find(".condensed .row-content");
  }

  addHighlight($activities, $transactionRows) {
    $activities.addClass("discrepancy-highlight");
    $transactionRows.addClass("discrepancy-highlight");
  }

  removeHighlight($activities, $transactionRows) {
    $activities.removeClass("discrepancy-highlight");
    $transactionRows.removeClass("discrepancy-highlight");
    this.clickedTransactionID = null;
  }

  /**
   * Add highlighting to a transaction.
   *
   * @param {object} activity - The activity to highlight.
   */
  toggleClickTransactionHighlight(activity) {
    const $matchingTransactionRow = this.getMatchingTransactionRow(activity);
    const transactionID = activity.dataset.transactionId;
    if (transactionID != this.clickedTransactionID) {
      // Remove highlighting from all other transactions and add it to this one
      this.removeHighlight(this.$discrepantActivities, this.$transactionRows);
      this.addHighlight($(activity), $matchingTransactionRow);
      // Update the tracker to indicate that an activity was clicked
      this.clickedTransactionID = transactionID;
    } else {
      this.removeHighlight($(activity), $matchingTransactionRow);
    }
  }

  /**
   * Add highlighting to a transaction.
   *
   * @param {object} activity - The activity to highlight.
   */
  addHoverTransactionHighlight(activity) {
    // Only add hover highlighting if a transaction has not been clicked
    if (this.clickedTransactionID == null) {
      const $matchingTransactionRow = this.getMatchingTransactionRow(activity);
      this.addHighlight($(activity), $matchingTransactionRow);
    }
  }

  /**
   * Remove highlighting from a transaction.
   *
   * @param {object} activity - The activity to stop highlighting.
   */
  removeHoverTransactionHighlight(activity) {
    // Only remove hover highlighting if a transaction has not been clicked
    if (this.clickedTransactionID == null) {
      const $matchingTransactionRow = this.getMatchingTransactionRow(activity);
      this.removeHighlight($(activity), $matchingTransactionRow);
    }
  }
}


(function() {

  const highlighter = new DiscrepancyHighlighter();

})();
