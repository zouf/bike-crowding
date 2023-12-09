const ctx = document.getElementById('timeSeriesChart').getContext('2d');
const labels = bikeData.map(d => moment(new Date(d.datetime)).format('MMM DD'));
const dataPoints = bikeData.map(d => d.raw_count);

const chart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: labels,
    datasets: [{
      label: 'Raw Count',
      data: dataPoints,
      backgroundColor: 'rgba(255, 99, 132, 0.2)',
      borderColor: 'rgba(255, 99, 132, 1)',
      borderWidth: 1
    }]
  },
  options: {
    responsive: true,
    scales: {
      xAxes: [{
        type: 'time',
        time: {
          unit: 'day'
        }
      }],
      yAxes: [{
        ticks: {
          beginAtZero: true
        }
      }]
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
