/*
 * Prepare a line graph of balances using the `chartist.js` library.
 *
 * Creates a chart using data (provided in the HTML template) for bank
 * balances over time. Data (x, y) pairs  are passed in as timestamps
 * calculated as seconds since the epoch and dollar values.
 */


function buildLabelInterpolationFunction(dateOptions) {

  function dateLabelInterpolation(value) {
    // Create a date object from the timestamp integer
    const date = new Date(value);
    const locale = "en-us";
    return date.toLocaleDateString(locale, dateOptions);
  }

  return dateLabelInterpolation;
}


function createBalanceChart(data) {

  const dataPoints = data.series[0].data
  // Set the number of labels per axis
  const xAxisDivisor = 5;
  const yAxisDivisor = 5;
  // Use the number of labels and the data to determine the date format
  const timestamps = dataPoints.map(point => point.x);
  const earliestTimestamp = Math.min(...timestamps);
  const latestTimestamp = Math.max(...timestamps);
  const millisecondsPerDay = 1000*60*60*24;
  const timestampRange = latestTimestamp - earliestTimestamp;
  const timestampDayRange =  timestampRange/millisecondsPerDay;
  // Show the day when timestamp range is (approx.) less than divisor months
  const showDay = (timestampDayRange < xAxisDivisor*30);
  let dateOptions = {
    year: "numeric",
    month: "short",
  };
  if (showDay) {
    dateOptions.day = "numeric";
  }
  // Use the data to determine the maximum y-value
  const balances = dataPoints.map(point => point.y);
  const maxBalance = Math.max(...balances);
  const magnitudeOrderExponent = Math.floor(Math.log10(maxBalance));
  const magnitudeOrder = Math.pow(10, magnitudeOrderExponent);
  const yLimit = Math.ceil(1.25*maxBalance/magnitudeOrder)*magnitudeOrder;

  let smoothLine = true;
  if (timestamps.length > 100) {
    smoothLine = false;
  }

  const options = {
    showPoint: false,
    lineSmooth: smoothLine,
    axisX: {
      type: Chartist.FixedScaleAxis,
      divisor: xAxisDivisor,
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
  new Chartist.LineChart("#balance-chart", data, options);

}


(function() {

  createBalanceChart(BALANCE_CHART_DATA);

})();
