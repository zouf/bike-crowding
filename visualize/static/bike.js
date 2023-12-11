
// Function to format datetime with ET
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
  return dateObj; 
}

// Format labels and data points
const labels = bikeData.map(d => formatDateTime(d.timestamp));
const dataPoints = bikeData.map(d => d.raw_count);
const imgLocations = bikeData.map(d => d.location);


// Calculate min and max values
const minValue = Math.min(...dataPoints);
const maxValue = Math.max(...dataPoints);

function getColor(value) {
  // Color mapping based on value
  const normalizedValue = (value - minValue) / (maxValue - minValue);
  const green = Math.round(255 * normalizedValue);
  const red = Math.round(255 * (1 - normalizedValue));
  return `rgba( ${green},${red}, 0, 0.5)`;
}

// Define Plotly data and layout
const data = [{
  type: 'scatter',
  mode: 'lines',
  x: labels,
  y: dataPoints,
  line: {
    // color: dataPoints.map(getColor),
    width: 1,
    shape: 'linear', // Change to 'linear' for a straight line
  },
  fill: false,
  hovertemplate: `Time: %{x}<br>Count: %{y}`, // Custom hover template
  customdata: imgLocations, // Add image locations as custom data

}];

const layout = {
  title: {
    text: 'Count of People in Central Park',
  },
  xaxis: {
    type: 'date',
    tickformat: '%a, %Y-%m-%d %I:%M%p', 
    tickangle: 10,
    autorange: true,
    title: {
      text: 'Time'
    }
  },
  yaxis: {
    title: {
      text: 'Value'
    },
    range: [minValue - 0.1 * (maxValue - minValue), maxValue + 0.1 * (maxValue - minValue)], // Add some padding
  },
  width: window.innerWidth,
  height: window.innerHeight * 0.8,
  responsive: true,
  legend: {
    visible: false, // Hide legend by default
  },
};


const timeSeriesChart = document.getElementById('timeSeriesChart');
const imageContainer = document.getElementById('img-div'); // Create a div for the image
imageContainer.id = 'imageContainer';
imageContainer.style.display = 'inline-block'; // Display the image container inline
imageContainer.style.verticalAlign = 'top'; // Align the container to the top

Plotly.newPlot(timeSeriesChart, data, layout);

// Add hover event listener
timeSeriesChart.on('plotly_hover', function (event) {
  const imageLocation = event.points[0].customdata;
  // Make an HTTP GET request to the image location
  fetch(imageLocation)
    .then(response => response.blob())
    .then(blob => {
      // Display the image
      const imageUrl = URL.createObjectURL(blob);
      const imageElement = document.createElement('img');
      imageElement.src = imageUrl;
      // Clear previous image
      while (imageContainer.firstChild) {
        imageContainer.removeChild(imageContainer.firstChild);
      }
      // Append the new image to the container
      imageContainer.appendChild(imageElement);
    });
});
