const ctx = document.getElementById('timeSeriesChart').getContext('2d');

// Define a function to format datetime with ET
function formatDateTime(datetimeStr) {
  const dateObj = new Date(datetimeStr);
  dateObj.setTime(dateObj.getTime() - dateObj.getTimezoneOffset() * 60 * 1000); // Convert from UTC to local time

  const options = {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "numeric",
    second: "numeric",
    timeZone: "America/New_York", // Set time zone to ET
  };
  return new Intl.DateTimeFormat("en-US", options).format(dateObj);
}

// Use the formatDateTime function to format labels
const labels = bikeData.map(d => formatDateTime(d.timestamp));
const dataPoints = bikeData.map(d => d.raw_count);

const maxValue = Math.max(...dataPoints);
const minValue = Math.min(...dataPoints);

// Define a color mapping function based on values
function getColor(value) {
  const normalizedValue = (value - minValue) / (maxValue - minValue);
  const green = Math.round(255 * normalizedValue);
  const red = Math.round(255 * (1 - normalizedValue));
  return `rgba( ${green},${red}, 0, 0.5)`;
}

// Register Luxon as the date adapter
Chart.register({
  id: 'luxon',
  beforeInit: function(chart) {
    const { options } = chart;
    if (options.scales.x.type === 'time' && options.scales.x.time && options.scales.x.time.parser) {
      options.scales.x.time.parser = function(value) {
        return DateTime.fromISO(value, { zone: 'utc' });
      };
    }
  }
});

const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: labels,
    datasets: [{
      label: 'Entity Count',
      data: dataPoints,
      backgroundColor: dataPoints.map(getColor), // Use custom color mapping function
      borderColor: 'rgba(0, 0, 0, 0.7)',
      borderWidth: 1,
      fill: false,
      cubicInterpolationMode: 'monotone',
      pointStyle: 'point',
      tension: 0.4

    }]
  },
  options: {
    responsive: true, // Disable responsiveness for maximizing size

    plugins: {
      title: {
        display: true,
        text: 'Count of People in Central Park'
      },
    },

    width: window.innerWidth, // Set width to full window width
    height: window.innerHeight * 0.8, // Set height to 80% of window height
    tooltips: {
      enabled: true,
      mode: 'point',
      callbacks: {
        label: function(tooltipItem) {
          // Format the tooltip label with additional information
          return `Time: ${tooltipItem.xLabel}, Count: ${tooltipItem.yLabel}`;
        }
      }
    },
    
    legend: {
      display: false
    },
    title: {
      display: true,
      text: 'Time Series Data'
    }
  }
});
