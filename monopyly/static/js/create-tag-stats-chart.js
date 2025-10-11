/*
 * Prepare a bar graph of tag statistics using the `chartist.js` library.
 *
 * Creates a chart using data (provided in the HTML template) for tag
 * statistics. Data is passed as a collection of series of monthly subtotals,
 * where each collection represents data for a given transaction tag.
 * Labels for the data are given as timestamps, each representing the
 * month corresponding to one element in each series.
 */


function buildLabelInterpolationFunction(dateOptions) {

  function dateLabelInterpolation(value) {
    // Create a date object from the timestamp integer
    const date = new Date(value);
    let dateString = "";
    if (date.getMonth() == 0) {
      const locale = "en-us";
      dateString = date.toLocaleDateString(locale, dateOptions);
    }
    return dateString;
  }

  return dateLabelInterpolation;
}


function createTagStatisticsChart(data) {

  // Set the number of labels per axis
  const yAxisDivisor = 5;
  // Use the number of labels and the data to determine the date format
  const timestamps = data.labels;
  const earliestTimestamp = Math.min(...timestamps);
  const latestTimestamp = Math.max(...timestamps);
  const millisecondsPerDay = 1000*60*60*24;
  const timestampWindowSize = latestTimestamp - earliestTimestamp;
  const timestampDayCount =  timestampWindowSize/millisecondsPerDay;
  let dateOptions = {
    year: "numeric",
  };
  // Use the data to determine the maximum y-value (nearest $500)
  const maxSubtotal = Math.max(...data.series.flat());
  const yLimit = Math.ceil(maxSubtotal/500)*500;

  const options = {
    axisX: {
      showGrid: false,
      labelInterpolationFnc: buildLabelInterpolationFunction(dateOptions),
    },
    axisY: {
      type: Chartist.FixedScaleAxis,
      divisor: yAxisDivisor,
      low: 0,
      high: yLimit,
      labelInterpolationFnc: function(value) {
        return "$" + value.toLocaleString();
      },
    },
  };
  new Chartist.BarChart("#tag-statistics-chart", data, options);
  // Dynamically set the width of the bars
  const $chart = $("#tag-statistics-chart");
  const barCount = data.series[0].length
  const calculatedBarWidth = Math.round(($chart.width() - 75) / barCount - 1);
  // Constrain the bar width between min/max values
  const minWidth = 2, maxWidth = 20;
  const barWidth = Math.max(Math.min(calculatedBarWidth, maxWidth), minWidth);
  $chart.css("--bar-width", `${barWidth}px`);
}


(function() {

  createTagStatisticsChart(TAG_STATISTICS_CHART_DATA);

})();


export { createTagStatisticsChart };
