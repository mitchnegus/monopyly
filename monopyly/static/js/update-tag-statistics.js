/*
 * Update the chart of transaction tag statistics.
 *
 * Update the tag statistics data based on the selected transaction tag.
 * It issues a POST request to the server to query the database based
 * on the user's selection. Once data is received, the bar chart showing
 * the data is updated.
 */

import {
  replaceDisplayContentsRequest
} from './modules/update-display-request.js';
import { createTagStatisticsChart } from './create-tag-stats-chart.js'


function updateTagStatisticsData() {

  const endpoint = UPDATE_STATISTICS_ENDPOINT;
  // Identify the chart container
  const $container = $('#tag-statistics-container');
  // Identify the select input
  const $selectTag = $('select#tag-options');

  // Send the request on select input update
  $selectTag.on("change", function() {
    const tagID = this.value;
    replaceDisplayContentsRequest(
      endpoint, tagID, $container, updateChart
    );
  });

}


function updateChart() {
  createTagStatisticsChart(TAG_STATISTICS_CHART_DATA);
}


(function() {

  updateTagStatisticsData();

})();
